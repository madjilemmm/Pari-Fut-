from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_matches():
    r = client.get("/matches?limit=5")
    assert r.status_code == 200
    matches = r.json()
    assert len(matches) <= 5
    for m in matches:
        assert m["league"] == "Premier League"


def test_prediction_probabilities_sum_to_one():
    matches = client.get("/matches?limit=1").json()
    match_id = matches[0]["match_id"]
    r = client.get(f"/matches/{match_id}/prediction")
    assert r.status_code == 200
    body = r.json()
    total = body["home_win_prob"] + body["draw_prob"] + body["away_win_prob"]
    assert abs(total - 1.0) < 1e-3


def test_unknown_match_returns_404():
    r = client.get("/matches/not-a-real-id/prediction")
    assert r.status_code == 404


def test_odds_returns_donnee_indisponible_not_fake_data():
    matches = client.get("/matches?limit=1").json()
    match_id = matches[0]["match_id"]
    r = client.get(f"/matches/{match_id}/odds")
    assert r.status_code == 501
    assert "indisponible" in r.json()["detail"].lower()
