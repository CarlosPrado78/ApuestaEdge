"""Retraso del plan Free: 2 h después de publicarse en el registro."""

import time

from app import db, ledger, providers, service


def _matches():
    matches, _src = providers.get_matches()
    assert matches
    return matches


def _publish(matches, created_at, min_edge=0.0):
    conn = db.connect()
    try:
        now = time.time()
        for rec in service.candidates_for_ledger(matches, min_edge=min_edge,
                                                 now=now):
            ledger.append_pick(conn, rec, created_at=created_at, source="live")
    finally:
        conn.close()


def test_free_sees_nothing_before_anything_is_published():
    out = service.build_recommendations(plan="free", matches=_matches(),
                                        source="live")
    assert out["count"] == 0


def test_free_sees_picks_published_two_hours_ago():
    matches = _matches()
    _publish(matches, created_at=time.time() - 3 * 3600)
    out = service.build_recommendations(plan="free", matches=matches,
                                        source="live")
    assert out["count"] > 0
    assert out["release_delay_seconds"] == 2 * 3600
    for p in out["picks"]:
        assert p["delayed"] is True
        assert "odds" not in p and "kelly" not in p
        assert p["explanation"]["summary"]


def test_free_does_not_see_fresh_picks():
    matches = _matches()
    _publish(matches, created_at=time.time() - 60)
    out = service.build_recommendations(plan="free", matches=matches,
                                        source="live")
    assert out["count"] == 0


def test_premium_is_not_delayed():
    matches = _matches()
    out = service.build_recommendations(plan="premium", matches=matches,
                                        source="live")
    assert out["count"] > 0
    assert all(p["delayed"] is False for p in out["picks"])


def test_demo_does_not_require_a_ledger():
    """Sin datos reales (demo) no hay registro público: se muestra la muestra."""
    matches = _matches()
    out = service.build_recommendations(plan="free", matches=matches,
                                        source="sample")
    assert out["count"] > 0
    assert out["release_delay_seconds"] == 0
    assert all(p["delayed"] is False for p in out["picks"])


def test_free_requests_do_not_share_mutable_state():
    matches = _matches()
    a = service.build_recommendations(plan="free", matches=matches,
                                      source="sample")
    a["picks"][0]["edge"] = 999.0
    a["picks"].clear()
    b = service.build_recommendations(plan="free", matches=matches,
                                      source="sample")
    assert b["count"] > 0 and b["picks"][0]["edge"] != 999.0
