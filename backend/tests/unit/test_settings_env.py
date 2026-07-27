from app.core.config import Settings


def test_settings_ignores_extra_values_from_shared_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "APP_DEBUG=true",
                "POSTGRES_DB=sgi",
                "POSTGRES_USER=sgi",
                "POSTGRES_PASSWORD=secret",
                "ENABLE_DIVIDENDS_SYNC=true",
                "DIVIDENDS_BATCH_SIZE=20",
            ]
        ),
        encoding="utf-8",
    )

    loaded = Settings(_env_file=env_file)

    assert loaded.APP_DEBUG is True
    assert not hasattr(loaded, "POSTGRES_DB")
    assert not hasattr(loaded, "ENABLE_DIVIDENDS_SYNC")
