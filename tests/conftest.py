"""Aísla la base de datos de los tests: nunca tocan la BD de desarrollo."""

import pytest

from app import config, main, service


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Cada test usa su propia SQLite temporal (seed incluido)."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test_apuesta_edge.db")
    service._clear_picks_cache()
    # El caché de partidos es global: sin esto, un test que lo deje en
    # "unavailable" contamina los siguientes.
    main._CACHE.update(ts=0.0, matches=None, source=None, updated_at=0.0)
    yield
    service._clear_picks_cache()
    main._CACHE.update(ts=0.0, matches=None, source=None, updated_at=0.0)
