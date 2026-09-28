from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IncidentStatusHistory


def make_asset(client: TestClient, name: str = "srv-web-01", **overrides) -> dict:
    response = client.post("/assets", json={"name": name, "asset_type": "server", **overrides})
    assert response.status_code == 201
    return response.json()


def make_vulnerability(client: TestClient, title: str = "OpenSSH RCE") -> dict:
    response = client.post("/vulnerabilities", json={"title": title, "severity": "high"})
    assert response.status_code == 201
    return response.json()


def make_incident(client: TestClient, **overrides) -> dict:
    payload = {"title": "Suspicious VPN logins", "severity": "high", **overrides}
    response = client.post("/incidents", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# --- create ---------------------------------------------------------------


def test_create_incident_starts_open_with_defaults(client: TestClient) -> None:
    incident = make_incident(client)

    assert incident["status"] == "open"
    assert incident["category"] == "other"
    assert incident["resolved_at"] is None and incident["closed_at"] is None
    assert incident["assets"] == [] and incident["vulnerabilities"] == []


def test_create_incident_links_assets_and_vulnerabilities(client: TestClient) -> None:
    asset = make_asset(client)
    vuln = make_vulnerability(client)

    incident = make_incident(client, asset_ids=[asset["id"]], vulnerability_ids=[vuln["id"]])

    assert [a["id"] for a in incident["assets"]] == [asset["id"]]
    assert [v["id"] for v in incident["vulnerabilities"]] == [vuln["id"]]


def test_duplicate_ids_are_deduplicated(client: TestClient) -> None:
    asset = make_asset(client)

    incident = make_incident(client, asset_ids=[asset["id"], asset["id"]])

    assert len(incident["assets"]) == 1


def test_create_writes_initial_audit_trail_entry(client: TestClient, db: Session) -> None:
    incident = make_incident(client)

    entries = db.scalars(
        select(IncidentStatusHistory).where(IncidentStatusHistory.incident_id == incident["id"])
    ).all()
    assert len(entries) == 1
    assert entries[0].from_status is None
    assert entries[0].to_status.value == "open"


def test_create_incident_rejects_invalid_payload(client: TestClient) -> None:
    invalid_payloads = [
        {"severity": "high"},  # missing title
        {"title": "x"},  # missing severity
        {"title": "", "severity": "high"},
        {"title": "x", "severity": "apocalyptic"},
        {"title": "x", "severity": "high", "category": "alien_invasion"},
        {"title": "x", "severity": "high", "asset_ids": ["a"]},
        {"title": "x", "severity": "high", "asset_ids": list(range(101))},
    ]
    for payload in invalid_payloads:
        assert client.post("/incidents", json=payload).status_code == 422, payload


def test_create_with_unknown_references_returns_422_and_creates_nothing(
    client: TestClient,
) -> None:
    asset = make_asset(client)

    response = client.post(
        "/incidents",
        json={"title": "x", "severity": "low", "asset_ids": [asset["id"], 777, 888]},
    )

    assert response.status_code == 422
    assert "777" in response.json()["detail"] and "888" in response.json()["detail"]
    assert client.get("/incidents").json() == []


def test_client_cannot_set_status_priority_or_id_on_create(client: TestClient) -> None:
    incident = make_incident(client, status="closed", priority="P1", id=999)

    assert incident["status"] == "open"
    assert incident["id"] != 999


# --- read -----------------------------------------------------------------


def test_get_incident_and_404(client: TestClient) -> None:
    asset = make_asset(client)
    created = make_incident(client, asset_ids=[asset["id"]])

    response = client.get(f"/incidents/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created
    assert client.get("/incidents/424242").status_code == 404


def test_list_returns_newest_first_without_nested_collections(client: TestClient) -> None:
    make_incident(client, title="first")
    make_incident(client, title="second")

    incidents = client.get("/incidents").json()

    assert [i["title"] for i in incidents] == ["second", "first"]
    assert "assets" not in incidents[0]


def test_list_filters(client: TestClient) -> None:
    asset = make_asset(client)
    make_incident(client, title="Phishing wave", category="phishing", severity="medium")
    make_incident(
        client, title="Ransomware on file server", category="malware", severity="critical",
        asset_ids=[asset["id"]],
    )
    make_incident(client, title="Misconfigured bucket", category="misconfiguration", severity="low")

    def titles(**params) -> list[str]:
        response = client.get("/incidents", params=params)
        assert response.status_code == 200
        return [i["title"] for i in response.json()]

    assert titles(severity="critical") == ["Ransomware on file server"]
    assert titles(category="phishing") == ["Phishing wave"]
    assert titles(status="open") == ["Misconfigured bucket", "Ransomware on file server", "Phishing wave"]
    assert titles(status="closed") == []
    assert titles(asset_id=asset["id"]) == ["Ransomware on file server"]
    assert titles(q="RANSOM") == ["Ransomware on file server"]
    assert titles(limit=1, skip=1) == ["Ransomware on file server"]


def test_list_rejects_invalid_filters(client: TestClient) -> None:
    assert client.get("/incidents", params={"status": "sleeping"}).status_code == 422
    assert client.get("/incidents", params={"limit": 0}).status_code == 422


# --- update ---------------------------------------------------------------


def test_patch_updates_only_sent_fields(client: TestClient) -> None:
    created = make_incident(client, description="orig", category="phishing")

    response = client.patch(f"/incidents/{created['id']}", json={"severity": "low"})

    assert response.status_code == 200
    updated = response.json()
    assert updated["severity"] == "low"
    assert updated["description"] == "orig"
    assert updated["category"] == "phishing"


def test_patch_replaces_linked_assets(client: TestClient) -> None:
    first = make_asset(client, "srv-01")
    second = make_asset(client, "srv-02")
    created = make_incident(client, asset_ids=[first["id"]])

    response = client.patch(f"/incidents/{created['id']}", json={"asset_ids": [second["id"]]})
    assert [a["id"] for a in response.json()["assets"]] == [second["id"]]

    response = client.patch(f"/incidents/{created['id']}", json={"asset_ids": []})
    assert response.json()["assets"] == []


def test_patch_cannot_change_status(client: TestClient) -> None:
    created = make_incident(client)

    response = client.patch(f"/incidents/{created['id']}", json={"status": "closed"})

    assert response.status_code == 200  # unknown field is ignored...
    assert response.json()["status"] == "open"  # ...and the state is untouched


def test_patch_with_unknown_reference_changes_nothing(client: TestClient) -> None:
    created = make_incident(client, title="original")

    response = client.patch(
        f"/incidents/{created['id']}", json={"title": "changed", "asset_ids": [777]}
    )

    assert response.status_code == 422
    assert client.get(f"/incidents/{created['id']}").json()["title"] == "original"


def test_patch_rejects_null_for_required_fields_and_missing_incident(client: TestClient) -> None:
    created = make_incident(client)
    url = f"/incidents/{created['id']}"

    assert client.patch(url, json={"title": None}).status_code == 422
    assert client.patch(url, json={"severity": None}).status_code == 422
    assert client.patch(url, json={"asset_ids": None}).status_code == 422
    assert client.patch("/incidents/424242", json={"title": "x"}).status_code == 404


# --- delete ---------------------------------------------------------------


def test_incidents_cannot_be_deleted(client: TestClient) -> None:
    """Decisão de desenho: o audit trail exige que os incidentes nunca se apaguem."""
    created = make_incident(client)

    assert client.delete(f"/incidents/{created['id']}").status_code == 405
    assert client.get(f"/incidents/{created['id']}").status_code == 200


def test_deleting_asset_keeps_incident(client: TestClient) -> None:
    asset = make_asset(client)
    created = make_incident(client, asset_ids=[asset["id"]])

    assert client.delete(f"/assets/{asset['id']}").status_code == 204

    remaining = client.get(f"/incidents/{created['id']}")
    assert remaining.status_code == 200
    assert remaining.json()["assets"] == []
