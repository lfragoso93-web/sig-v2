"""CLI offline da prova de idempotência do estágio de proventos."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.pre_prod_dividends_seed_contract import (
    DividendsSeedContractError,
)
from app.services.pre_prod_dividends_seed_idempotency import (
    compare_dividends_seed_files,
)

EXIT_OK = 0
EXIT_NOT_IDEMPOTENT = 1
EXIT_INVALID_INPUT = 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compara offline duas evidências consecutivas do seed de proventos"
        )
    )
    parser.add_argument("--first", required=True, type=Path)
    parser.add_argument("--second", required=True, type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        result = compare_dividends_seed_files(args.first, args.second)
    except (DividendsSeedContractError, KeyError, TypeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "evidência inválida",
                    "type": type(exc).__name__,
                },
                ensure_ascii=False,
            )
        )
        return EXIT_INVALID_INPUT

    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return EXIT_OK if result.ok else EXIT_NOT_IDEMPOTENT


if __name__ == "__main__":
    raise SystemExit(main())
