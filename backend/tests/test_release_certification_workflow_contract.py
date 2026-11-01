import base64
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-oci.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _embedded_python(source: str, command_fragment: str) -> str:
    line = next(
        line
        for line in source.splitlines()
        if command_fragment in line and "base64.b64decode" in line
    )
    match = re.search(r"base64\.b64decode\('([A-Za-z0-9+/=]+)'\)", line)
    assert match is not None
    return base64.b64decode(match.group(1)).decode("ascii")


def test_production_release_certification_is_after_ci_and_smoke_gates() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert 'workflows: ["SIG v2 CI/CD"]' in source
    assert "github.event.workflow_run.conclusion == 'success'" in source
    assert "github.event.workflow_run.event == 'push'" in source
    assert "github.event.workflow_run.head_branch == 'main'" in source
    assert 'TARGET_SHA: ${{ github.event.workflow_run.head_sha ||' in source
    assert "CI_WORKFLOW_RUN_ID: ${{ github.event.workflow_run.id ||" in source

    smoke = source.index("sh scripts/oci_smoke_test.sh")
    persisted_identity = source.index("Persistindo a identidade implantada")
    dry_run = source.index("CERT_DRY_RUN=")
    execute = source.index("--execute", dry_run)
    ready = source.index("Validando prontid")
    assert smoke < persisted_identity < dry_run < execute < ready
    assert "--confirmation \"${CERT_CONFIRMATION}\"" in source
    assert '${CERT_MODE}" != "already-certified"' in source


def test_deploy_validates_predeploy_backup_before_checkout_and_rotates_only_backup_runs() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    backup = source.index("Criando e validando backup da base")
    checkout = source.index('git checkout "${TARGET_BRANCH}"', backup)
    build = source.index("compose build backend", checkout)
    validate_backup = source.index("app.cli.real_data_dataset_identity", backup)
    initializer = _embedded_python(
        source, "compose exec -T --user 0 backend python -c"
    )
    rotation = _embedded_python(
        source, "compose exec -T backend python -c"
    )
    rotation_command = source.index(
        "compose exec -T backend python -c", validate_backup
    )

    assert backup < checkout < build
    assert backup < validate_backup < rotation_command < checkout
    assert "shutil.rmtree(candidate)" in rotation
    assert "oci-predeploy-backups" in source
    assert "compose exec -T --user 0 backend python -c" in source
    assert "python - /app/artifacts <<'PY'" not in source
    assert "chown -R" not in source
    assert 'candidate.name.startswith("run-")' in rotation
    assert "resolved_candidate.parent!=resolved_root" in rotation
    assert ' "${PREDEPLOY_RUN_ID}"' in source
    assert "postgres_data" not in source
    assert "volume prune" not in source
    assert "compose down -v" not in source


def test_embedded_backup_initializer_executes_and_chowns_only_dedicated_root(
    tmp_path, monkeypatch
) -> None:
    import os
    import sys

    import pytest

    source = WORKFLOW.read_text(encoding="utf-8")
    initializer = _embedded_python(
        source, "compose exec -T --user 0 backend python -c"
    )
    script = compile(initializer, "oci-backup-initializer", "exec")

    parent = tmp_path / "artifacts"
    parent.mkdir()
    ownership_changes = []

    def record_chown(path, uid, gid):
        ownership_changes.append((Path(path), uid, gid))

    from pathlib import Path

    monkeypatch.setattr(os, "chown", record_chown, raising=False)
    monkeypatch.setattr(sys, "argv", ["initializer", str(parent)])
    exec(script, {"__name__": "__main__"})

    root = parent / "oci-predeploy-backups"
    assert root.is_dir()
    assert ownership_changes == [(root, 1000, 1000)]
    if os.name == "posix":
        assert root.stat().st_mode & 0o777 == 0o700

    outside = tmp_path / "outside"
    outside.mkdir()
    link_parent = tmp_path / "artifacts-link"
    try:
        link_parent.symlink_to(outside, target_is_directory=True)
    except OSError:
        return

    monkeypatch.setattr(sys, "argv", ["initializer", str(link_parent)])
    with pytest.raises(SystemExit, match="artifact mount"):
        exec(script, {"__name__": "__main__"})
    assert not (outside / "oci-predeploy-backups").exists()

    second_parent = tmp_path / "artifacts2"
    second_parent.mkdir()
    outside_root = tmp_path / "outside-root"
    outside_root.mkdir()
    (outside_root / "keep.txt").write_text("preserve", encoding="utf-8")
    backup_link = second_parent / "oci-predeploy-backups"
    try:
        backup_link.symlink_to(outside_root, target_is_directory=True)
    except OSError:
        return
    monkeypatch.setattr(sys, "argv", ["initializer", str(second_parent)])
    with pytest.raises(SystemExit, match="regular directory"):
        exec(script, {"__name__": "__main__"})
    assert (outside_root / "keep.txt").read_text(encoding="utf-8") == "preserve"


def test_deploy_gate_invokes_release_cli_with_workflow_identity() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert source.count("python -m app.cli.real_data_release_certification") == 2
    for option in (
        "--expected-sha",
        "--workflow-run-id",
        "--workflow-run-conclusion",
        "--workflow-run-event",
        "--workflow-run-branch",
        "--smoke-test-passed",
        "--report-file",
    ):
        assert source.count(option) >= 2
    assert "curl -fsS http://localhost:8000/ready" in source


def test_smoke_test_uses_the_same_explicit_compose_project_as_deploy() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "COMPOSE_PROJECT_NAME=sig-v2 sh scripts/oci_smoke_test.sh" in source


def test_post_commit_failures_report_persisted_certification_state(
    monkeypatch, capsys
) -> None:
    import json

    import pytest

    from app.cli import real_data_release_certification as cli

    error = cli.RealDataReleasePostCommitError(
        "report write failed after commit",
        database_writes_executed=1,
        event_key="release-event-123",
    )

    def fail_run(coro):
        coro.close()
        raise error

    monkeypatch.setattr(cli.asyncio, "run", fail_run)

    with pytest.raises(SystemExit) as raised:
        cli.main(
            [
                "--expected-sha", "a" * 40,
                "--workflow-run-id", "12345",
                "--workflow-run-conclusion", "success",
                "--workflow-run-event", "push",
                "--workflow-run-branch", "main",
                "--report-file", "/tmp/release-report.json",
            ]
        )

    assert raised.value.code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["database_writes_executed"] == 1
    assert payload["transaction_committed"] is True
    assert payload["plan_event_key"] == "release-event-123"


def test_ambiguous_commit_is_not_reported_as_zero_writes(
    monkeypatch, capsys
) -> None:
    import json

    import pytest

    from app.cli import real_data_release_certification as cli

    error = cli.RealDataReleaseCommitOutcomeUnknownError(
        event_key="release-event-uncertain"
    )

    def fail_run(coro):
        coro.close()
        raise error

    monkeypatch.setattr(cli.asyncio, "run", fail_run)

    with pytest.raises(SystemExit) as raised:
        cli.main(
            [
                "--expected-sha", "a" * 40,
                "--workflow-run-id", "12345",
                "--workflow-run-conclusion", "success",
                "--workflow-run-event", "push",
                "--workflow-run-branch", "main",
                "--report-file", "/tmp/release-report.json",
            ]
        )

    assert raised.value.code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["database_writes_executed"] is None
    assert payload["transaction_committed"] is None
    assert payload["plan_event_key"] == "release-event-uncertain"



def test_backup_branch_guard_explicitly_allows_main_and_dev_branch() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert (
        'if [ "${PREDEPLOY_BRANCH}" != "main" ] && '
        '[ "${PREDEPLOY_BRANCH}" != "stable-15jun" ]; then'
    ) in source


def test_backend_health_wait_is_embedded_as_one_ssh_safe_python_command() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    payloads = re.findall(
        r"base64\.b64decode\('([A-Za-z0-9+/=]+)'\)", source
    )
    decoded = [base64.b64decode(payload).decode("ascii") for payload in payloads]
    health_wait = next(payload for payload in decoded if "urlopen(" in payload)

    compile(health_wait, "<oci-health-wait>", "exec")
    assert "range(15)" in health_wait
    assert "time.sleep(2)" in health_wait
    assert "for i in $(seq 1 15)" not in source
    assert not any("<<" in line for line in source.splitlines())


def test_oci_smoke_cloudflared_diagnostics_suppress_candidate_values() -> None:
    smoke = (ROOT / "scripts" / "oci_smoke_test.sh").read_text(encoding="utf-8")

    assert 'grep -nEo "$TOKEN_PATTERN"' in smoke
    assert "candidate line=%s length=%d classes=%s" in smoke
    assert "candidate values suppressed" in smoke
    assert 'fail "cloudflared logs may contain token-like content' in smoke

    assert 'printf "[oci-smoke-test] token-like candidate' in smoke

def test_cloudflared_token_is_mounted_as_a_secret_file_and_not_an_env_value() -> None:
    compose = (ROOT / "docker-compose.oci.yml").read_text(encoding="utf-8")
    deploy = WORKFLOW.read_text(encoding="utf-8")
    smoke = (ROOT / "scripts" / "oci_smoke_test.sh").read_text(encoding="utf-8")

    assert "TUNNEL_TOKEN_FILE: /run/secrets/cloudflare_tunnel_token" in compose
    assert 'user: "${CLOUDFLARED_UID:-1000}"' in compose
    assert "cloudflare_tunnel_token:" in compose
    assert "file: ${CLOUDFLARE_TUNNEL_TOKEN_FILE:-.cloudflared/tunnel-token}" in compose
    assert "env_file:" not in compose
    assert "TUNNEL_TOKEN: ${CLOUDFLARE_TUNNEL_TOKEN" not in compose

    token_file_ready = deploy.index('CLOUDFLARED_TOKEN_FILE="${CLOUDFLARED_TOKEN_DIR}/tunnel-token"')
    first_compose_exec = deploy.index("compose exec -T --user 0 backend python -c")
    tunnel_restart = deploy.index("compose up -d --no-deps --force-recreate cloudflared")
    smoke_run = deploy.index("sh scripts/oci_smoke_test.sh")
    assert token_file_ready < first_compose_exec
    assert tunnel_restart < smoke_run
    assert "compose up -d --no-deps --force-recreate cloudflared" in deploy
    assert "chmod 700" in deploy
    assert 'chmod 400 "${CLOUDFLARED_TOKEN_TMP}"' in deploy
    assert 'export CLOUDFLARED_UID="$(id -u)"' in deploy
    assert "config --environment | awk" in deploy

    assert "umask 077" in smoke
    assert 'trap \'rm -f -- "${CLOUDFLARED_LOG}" "${CLOUDFLARED_SANITIZED_LOG}"\' EXIT' in smoke
