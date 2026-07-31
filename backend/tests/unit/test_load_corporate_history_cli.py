from argparse import Namespace
from datetime import date

import pytest

from app.cli.load_corporate_history import _validate


def _arguments(**changes):
    values = {
        "run_id": "20260731-190000",
        "date_from": date(2000, 1, 1),
        "date_to": date(2026, 7, 31),
        "apply": False,
        "authorization": "",
    }
    values.update(changes)
    return Namespace(**values)


def test_dry_run_does_not_require_apply_authorization() -> None:
    _validate(_arguments())


def test_apply_requires_exact_authorization_phrase() -> None:
    with pytest.raises(ValueError, match="authorization"):
        _validate(_arguments(apply=True))

    _validate(
        _arguments(
            apply=True,
            authorization="I-AUTHORIZE-CORPORATE-HISTORY",
        )
    )


def test_run_id_and_window_are_strict() -> None:
    with pytest.raises(ValueError, match="run_id"):
        _validate(_arguments(run_id="manual"))
    with pytest.raises(ValueError, match="date_from"):
        _validate(_arguments(date_from=date(2026, 7, 31), date_to=date(2000, 1, 1)))
