from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-oci.yml"


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
    checkout = source.index('git checkout "${TARGET_BRANCH}"')
    build = source.index("compose build backend")
    validate_backup = source.index("app.cli.real_data_dataset_identity")
    rotate = source.index("shutil.rmtree(candidate)")

    assert backup < checkout < build
    assert backup < validate_backup < rotate < checkout
    assert "oci-predeploy-backups" in source
    assert 'candidate.name.startswith("run-")' in source
    assert "resolved_candidate.parent != resolved_root" in source
    assert "postgres_data" not in source
    assert "volume prune" not in source
    assert "compose down -v" not in source


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
