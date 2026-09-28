from fastapi.testclient import TestClient


def preflight(client: TestClient, origin: str):
    return client.options(
        "/incidents",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )


def test_configured_origin_is_allowed(client: TestClient) -> None:
    response = preflight(client, "http://localhost:5173")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_other_origins_are_not_allowed(client: TestClient) -> None:
    response = preflight(client, "https://evil.example")

    assert "access-control-allow-origin" not in response.headers


def test_wildcard_is_never_used(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] != "*"
