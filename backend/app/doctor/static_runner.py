"""Runner focado dos gates estáticos já existentes.

Somente arquivos de teste explicitamente associados a checks ``static`` podem
ser executados. O módulo não conhece banco, runtime, provedores ou operações de
escrita da aplicação.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys

from app.doctor.catalog import architecture_check_by_id
from app.doctor.contracts import (
    DoctorCheckKind,
    DoctorExitCode,
    DoctorFindingResult,
    DoctorFindingStatus,
    resolve_exit_code,
)


@dataclass(frozen=True)
class StaticCheckExecution:
    return_code: int
    output: str = ""


StaticCheckExecutor = Callable[[tuple[str, ...], Path], StaticCheckExecution]


@dataclass(frozen=True)
class StaticDoctorReport:
    results: tuple[DoctorFindingResult, ...]
    exit_code: DoctorExitCode


def _execute_pytest(
    command: tuple[str, ...], backend_root: Path
) -> StaticCheckExecution:
    completed = subprocess.run(
        command,
        cwd=backend_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return StaticCheckExecution(completed.returncode, completed.stdout)


def _test_paths(finding_id: str, repository_root: Path) -> tuple[Path, ...]:
    entry = architecture_check_by_id[finding_id]
    tests_root = (repository_root / "backend" / "tests").resolve()
    paths: list[Path] = []

    for evidence in entry.evidence:
        path = (repository_root / evidence).resolve()
        if path.parent != tests_root or not path.name.startswith("test_"):
            raise ValueError(
                f"{finding_id} possui evidência não executável no runner estático: "
                f"{evidence}"
            )
        if not path.is_file():
            raise FileNotFoundError(f"evidência ausente para {finding_id}: {evidence}")
        paths.append(path)

    return tuple(paths)


def _command(paths: Sequence[Path], backend_root: Path) -> tuple[str, ...]:
    relative_paths = tuple(str(path.relative_to(backend_root)) for path in paths)
    return (
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        *relative_paths,
    )


def _execution_detail(execution: StaticCheckExecution) -> str:
    detail = f"pytest exit_code={execution.return_code}"
    if execution.return_code != 0 and execution.output.strip():
        detail += f"; output={execution.output.strip()[-4000:]}"
    return detail


def _status(return_code: int) -> DoctorFindingStatus:
    if return_code == 0:
        return DoctorFindingStatus.PASS
    if return_code == 1:
        return DoctorFindingStatus.FAIL
    return DoctorFindingStatus.ERROR


def run_static_checks(
    finding_ids: Sequence[str],
    *,
    repository_root: Path,
    executor: StaticCheckExecutor = _execute_pytest,
) -> StaticDoctorReport:
    """Executa somente os IDs estáticos solicitados, um gate por resultado."""

    if len(set(finding_ids)) != len(finding_ids):
        raise ValueError("finding_ids não pode conter IDs duplicados")

    backend_root = (repository_root / "backend").resolve()
    results: list[DoctorFindingResult] = []
    batch_failure: StaticCheckExecution | None = None

    entries = [architecture_check_by_id.get(finding_id) for finding_id in finding_ids]
    can_batch = len(entries) > 1 and all(
        entry is not None and entry.kind is DoctorCheckKind.STATIC for entry in entries
    )
    if can_batch:
        try:
            unique_paths = tuple(
                dict.fromkeys(
                    path
                    for finding_id in finding_ids
                    for path in _test_paths(finding_id, repository_root.resolve())
                )
            )
            batch_execution = executor(
                _command(unique_paths, backend_root), backend_root
            )
        except (OSError, ValueError) as exc:
            frozen_results = tuple(
                DoctorFindingResult(
                    finding_id=finding_id,
                    status=DoctorFindingStatus.ERROR,
                    detail=f"falha no lote estático: {exc}",
                )
                for finding_id in finding_ids
            )
            return StaticDoctorReport(
                results=frozen_results,
                exit_code=resolve_exit_code(
                    frozen_results, architecture_check_by_id
                ),
            )

        if batch_execution.return_code == 0:
            frozen_results = tuple(
                DoctorFindingResult(
                    finding_id=finding_id,
                    status=DoctorFindingStatus.PASS,
                    detail="pytest batch exit_code=0",
                )
                for finding_id in finding_ids
            )
            return StaticDoctorReport(
                results=frozen_results,
                exit_code=resolve_exit_code(
                    frozen_results, architecture_check_by_id
                ),
            )
        batch_failure = batch_execution

    for finding_id in finding_ids:
        entry = architecture_check_by_id.get(finding_id)
        if entry is None:
            results.append(
                DoctorFindingResult(
                    finding_id=finding_id,
                    status=DoctorFindingStatus.ERROR,
                    detail="ID não existe no catálogo",
                )
            )
            continue
        if entry.kind is not DoctorCheckKind.STATIC:
            results.append(
                DoctorFindingResult(
                    finding_id=finding_id,
                    status=DoctorFindingStatus.ERROR,
                    detail=f"check {entry.kind.value} não é permitido pelo runner estático",
                )
            )
            continue

        try:
            paths = _test_paths(finding_id, repository_root.resolve())
            execution = executor(_command(paths, backend_root), backend_root)
        except (OSError, ValueError) as exc:
            results.append(
                DoctorFindingResult(
                    finding_id=finding_id,
                    status=DoctorFindingStatus.ERROR,
                    detail=str(exc),
                )
            )
            continue

        status = _status(execution.return_code)
        detail = _execution_detail(execution)
        results.append(
            DoctorFindingResult(
                finding_id=finding_id,
                status=status,
                detail=detail,
            )
        )

    if batch_failure is not None and all(
        result.status is DoctorFindingStatus.PASS for result in results
    ):
        batch_detail = _execution_detail(batch_failure)
        results = [
            DoctorFindingResult(
                finding_id=result.finding_id,
                status=DoctorFindingStatus.ERROR,
                detail=f"lote falhou, mas isolamento passou; {batch_detail}",
            )
            for result in results
        ]

    frozen_results = tuple(results)
    return StaticDoctorReport(
        results=frozen_results,
        exit_code=resolve_exit_code(frozen_results, architecture_check_by_id),
    )
