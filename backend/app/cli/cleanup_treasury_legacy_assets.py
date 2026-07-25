"""Valida ou aplica a limpeza transacional dos legados Educa+ 4742/4747."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from sqlalchemy import create_engine

from app.core.config import settings
from app.services.treasury_legacy_cleanup import TreasuryLegacyCleanupError, execute


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="autoriza a transação real; ausente, executa somente dry-run",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                report = execute(connection, apply=arguments.apply)
                if arguments.apply:
                    transaction.commit()
                else:
                    transaction.rollback()
            except Exception:
                transaction.rollback()
                raise
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 0
    except TreasuryLegacyCleanupError as exc:
        print(
            json.dumps(
                {
                    "schema_version": "treasury-legacy-cleanup.v1",
                    "status": "rejected",
                    "mode": "apply" if arguments.apply else "dry-run",
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2
    finally:
        engine.dispose()


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
