"""Emite o readiness read-only para testes assistidos com usuarios."""
from __future__ import annotations

import asyncio
import json
import logging
import sys

from app.core.database import AsyncSessionLocal
from app.services.user_test_readiness_service import build_user_test_readiness


def _configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


async def _main() -> int:
    async with AsyncSessionLocal() as db:
        report = await build_user_test_readiness(db)
        await db.rollback()
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.go_for_assisted_user_tests else 1


def main() -> None:
    _configure_utf8_output()
    logging.basicConfig(level=logging.INFO)
    try:
        code = asyncio.run(_main())
    except KeyboardInterrupt:
        code = 130
    except Exception:
        logging.getLogger(__name__).exception("user-test readiness falhou")
        code = 1
    raise SystemExit(code)


if __name__ == "__main__":
    main()
