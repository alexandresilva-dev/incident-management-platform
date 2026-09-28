from fastapi.testclient import TestClient


def make_asset(client: TestClient, **overrides) -> dict:
    payload = {"name": "srv-web-01", "asset_type": "server", **overrides}
    response = client.post("/assets", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# --- create ---------------------------------------------------------------


def test_create_asset_applies_defaults(client: TestClient) -> None:
    asset = make_asset(client)

    assert asset["id"] > 0
    assert asset["name"] == "srv-web-01"
    assert asset["criticality"] == "medium"
    assert asset["ip_address"] is None
    assert asset["created_at"] and asset["updated_at"]


def test_create_asset_normalises_input(client: TestClient) -> None:
    asset = make_asset(client, name="  srv-db-01  ", ip_address="2001:0db8:0000:0000:0000:0000:0000:0001")

    assert asset["name"] == "srv-db-01"
    assert asset["ip_address"] == "2001:db8::1"


def test_create_asset_rejects_invalid_payload(client: TestClient) -> None:
    invalid_payloads = [
        {"asset_type": "server"},  # missing name
        {"name": "", "asset_type": "server"},  # empty name
        {"name": "   ", "asset_type": "server"},  # blank name
        {"name": "x", "asset_type": "toaster"},  # unknown type
        {"name": "x", "asset_type": "server", "criticality": "urgent"},  # unknown criticality
        {"name": "x", "asset_type": "server", "ip_address": "999.1.1.1"},  # bad ip
        {"name": "x" * 201, "asset_type": "server"},  # too long
    ]
    for payload in invalid_payloads:
        response = client.post("/assets", json=payload)
        assert response.status_code == 422, payload


def test_client_cannot_set_id_or_timestamps(client: TestClient) -> None:
    asset = make_asset(client, id=999, created_at="2000-01-01T00:00:00Z")

    assert asset["id"] != 999
    assert not asset["created_at"].startswith("2000")


# --- read -----------------------------------------------------------------


def test_get_asset(client: TestClient) -> None:
    created = make_asset(client)

    response = client.get(f"/assets/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_missing_asset_returns_404(client: TestClient) -> None:
    response = client.get("/assets/424242")

    assert response.status_code == 404
    assert response.json()["detail"] == "Asset 424242 not found"


def test_list_assets_filters_and_paginates(client: TestClient) -> None:
    make_asset(client, name="srv-web-01", asset_type="server", criticality="high")
    make_asset(client, name="srv-web-02", asset_type="server", criticality="low")
    make_asset(client, name="crm-app", asset_type="application", criticality="high")

    def names(**params) -> list[str]:
        response = client.get("/assets", params=params)
        assert response.status_code == 200
        return [a["name"] for a in response.json()]

    assert names() == ["srv-web-01", "srv-web-02", "crm-app"]
    assert names(asset_type="server") == ["srv-web-01", "srv-web-02"]
    assert names(criticality="high") == ["srv-web-01", "crm-app"]
    assert names(asset_type="server", criticality="high") == ["srv-web-01"]
    assert names(q="WEB") == ["srv-web-01", "srv-web-02"]
    assert names(limit=1, skip=1) == ["srv-web-02"]


def test_list_search_treats_wildcards_literally(client: TestClient) -> None:
    make_asset(client, name="srv-web-01")

    response = client.get("/assets", params={"q": "%"})

    assert response.json() == []


def test_list_rejects_invalid_pagination(client: TestClient) -> None:
    assert client.get("/assets", params={"limit": 0}).status_code == 422
    assert client.get("/assets", params={"limit": 1000}).status_code == 422
    assert client.get("/assets", params={"skip": -1}).status_code == 422


# --- update ---------------------------------------------------------------


def test_patch_updates_only_sent_fields(client: TestClient) -> None:
    created = make_asset(client, owner="ops", criticality="low")

    response = client.patch(f"/assets/{created['id']}", json={"criticality": "critical"})

    assert response.status_code == 200
    updated = response.json()
    assert updated["criticality"] == "critical"
    assert updated["owner"] == "ops"  # unchanged
    assert updated["name"] == created["name"]


def test_patch_can_clear_optional_field(client: TestClient) -> None:
    created = make_asset(client, owner="ops")

    response = client.patch(f"/assets/{created['id']}", json={"owner": None})

    assert response.status_code == 200
    assert response.json()["owner"] is None


def test_patch_rejects_null_for_required_field(client: TestClient) -> None:
    created = make_asset(client)

    response = client.patch(f"/assets/{created['id']}", json={"name": None})

    assert response.status_code == 422


def test_patch_missing_asset_returns_404(client: TestClient) -> None:
    assert client.patch("/assets/424242", json={"name": "x"}).status_code == 404


# --- delete ---------------------------------------------------------------


def test_delete_asset(client: TestClient) -> None:
    created = make_asset(client)

    assert client.delete(f"/assets/{created['id']}").status_code == 204
    assert client.get(f"/assets/{created['id']}").status_code == 404


def test_delete_missing_asset_returns_404(client: TestClient) -> None:
    assert client.delete("/assets/424242").status_code == 404
