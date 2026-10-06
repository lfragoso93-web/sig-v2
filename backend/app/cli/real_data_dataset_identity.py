"""Read-only CLI that derives a canonical real-data dataset reference."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from app.services.real_data_dataset_identity import (
    DATASET_IDENTITY_SCHEMA_VERSION,
    build_real_data_dataset_identity,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Valida um backup consistente e emite a referencia canonica do "
            "dataset sem alterar o banco ou os artefatos."
        )
    )
    parser.add_argument("--artifact-directory", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    try:
        identity = build_real_data_dataset_identity(
            _parser().parse_args(argv).artifact_directory
        )
        print(json.dumps(identity.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        exit_code = 0
    except KeyboardInterrupt:
        exit_code = 130
    except Exception as exc:  # noqa: BLE001 - administrative CLI boundary
        print(
            json.dumps(
                {
                    "schema_version": DATASET_IDENTITY_SCHEMA_VERSION,
                    "ok": False,
                    "database_writes_executed": 0,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        exit_code = 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
