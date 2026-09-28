import re

from fastapi.testclient import TestClient

from app.main import app

# As únicas rotas que não exigem token. Qualquer rota nova tem de ser protegida
# ou aparecer aqui de forma explícita (e revista).
PUBLIC_ROUTES = {
    ("GET", "/health"),
    ("POST", "/auth/login"),
}

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def test_every_route_except_the_public_ones_requires_authentication(
    anonymous_client: TestClient,
) -> None:
    # O esquema OpenAPI é a interface pública da app: lista todos os caminhos e métodos.
    paths = app.openapi()["paths"]
    checked = 0
    for path, operations in paths.items():
        for method in operations:
            if method not in HTTP_METHODS or (method.upper(), path) in PUBLIC_ROUTES:
                continue
            url = re.sub(r"\{[^}]+\}", "1", path)  # /incidents/{incident_id} -> /incidents/1
            response = anonymous_client.request(method.upper(), url)
            assert response.status_code == 401, f"{method.upper()} {path} is not protected"
            assert response.headers["www-authenticate"] == "Bearer"
            checked += 1

    assert checked >= 15  # garante que o teste não passa "vazio"


def test_public_routes_are_really_public(anonymous_client: TestClient) -> None:
    assert anonymous_client.get("/health").status_code == 200
    # /auth/login é público: sem credenciais devolve 422 (formulário em falta), não 401.
    assert anonymous_client.post("/auth/login").status_code == 422


def test_tokens_from_other_places_do_not_work(anonymous_client: TestClient) -> None:
    for header in ["Bearer not-a-real-token", "Bearer null", "Bearer undefined"]:
        response = anonymous_client.get("/incidents", headers={"Authorization": header})
        assert response.status_code == 401


def test_audit_trail_records_who_acted(client: TestClient) -> None:
    created = client.post("/incidents", json={"title": "Who did it", "severity": "low"}).json()
    client.post(f"/incidents/{created['id']}/transitions", json={"to_status": "investigating"})

    history = client.get(f"/incidents/{created['id']}/history").json()

    assert [entry["changed_by"] for entry in history] == ["tester@example.com"] * 2
