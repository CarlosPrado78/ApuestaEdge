"""Aísla la base de datos de los tests: nunca tocan la BD de desarrollo."""

import pytest

from app import config


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Cada test usa su propia SQLite temporal (seed incluido)."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test_apuesta_edge.db")
    # En tests se permite el login directo (sin correo) para poder arrancar sesión.
    monkeypatch.setenv("AUTH_DEV_LOGIN", "1")
    monkeypatch.setenv("AUTH_DEV_MODE", "1")
    yield
