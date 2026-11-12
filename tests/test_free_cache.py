"""El caché de picks Free no debe compartir estado entre peticiones."""

from app import providers, service


def test_free_picks_survive_repeated_requests():
    matches, src = providers.get_matches()
    first = service.build_recommendations(plan="free", matches=matches, source=src)
    for _ in range(3):
        again = service.build_recommendations(plan="free", matches=matches, source=src)
        assert again["count"] == first["count"] > 0
        for p in again["picks"]:
            assert "odds" not in p and "kelly" not in p
            assert p["explanation"]["summary"]


def test_cached_picks_are_isolated_from_callers():
    matches, src = providers.get_matches()
    a = service.build_recommendations(plan="free", matches=matches, source=src)
    a["picks"][0]["edge"] = 999.0
    a["picks"].clear()
    b = service.build_recommendations(plan="free", matches=matches, source=src)
    assert b["count"] > 0 and b["picks"][0]["edge"] != 999.0
