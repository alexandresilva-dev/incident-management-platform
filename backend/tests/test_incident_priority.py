from fastapi.testclient import TestClient


def make_asset(client: TestClient, name: str, criticality: str = "medium") -> dict:
    response = client.post(
        "/assets", json={"name": name, "asset_type": "server", "criticality": criticality}
    )
    assert response.status_code == 201
    return response.json()


def make_incident(client: TestClient, severity: str = "medium", **overrides) -> dict:
    payload = {"title": f"{severity} incident", "severity": severity, **overrides}
    response = client.post("/incidents", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def priority_of(client: TestClient, incident_id: int) -> str:
    return client.get(f"/incidents/{incident_id}").json()["priority"]


def close(client: TestClient, incident_id: int) -> None:
    for target in ("investigating", "mitigated", "resolved", "closed"):
        response = client.post(f"/incidents/{incident_id}/transitions", json={"to_status": target})
        assert response.status_code == 200


# --- on create / update ----------------------------------------------------


def test_priority_follows_severity_on_create(client: TestClient) -> None:
    assert make_incident(client, "critical")["priority"] == "P1"
    assert make_incident(client, "high")["priority"] == "P2"
    assert make_incident(client, "medium")["priority"] == "P3"
    assert make_incident(client, "low")["priority"] == "P4"


def test_critical_asset_escalates_priority_on_create(client: TestClient) -> None:
    payments = make_asset(client, "payments-db", "critical")

    incident = make_incident(client, "medium", asset_ids=[payments["id"]])

    assert incident["priority"] == "P2"


def test_changing_severity_recalculates_priority(client: TestClient) -> None:
    incident = make_incident(client, "low")
    assert incident["priority"] == "P4"

    updated = client.patch(f"/incidents/{incident['id']}", json={"severity": "critical"}).json()

    assert updated["priority"] == "P1"


def test_linking_and_unlinking_a_critical_asset_recalculates_priority(client: TestClient) -> None:
    payments = make_asset(client, "payments-db", "critical")
    incident = make_incident(client, "medium")
    url = f"/incidents/{incident['id']}"

    assert client.patch(url, json={"asset_ids": [payments["id"]]}).json()["priority"] == "P2"
    assert client.patch(url, json={"asset_ids": []}).json()["priority"] == "P3"


def test_client_cannot_set_priority_directly(client: TestClient) -> None:
    incident = make_incident(client, "low")

    response = client.patch(f"/incidents/{incident['id']}", json={"priority": "P1"})

    assert response.status_code == 200
    assert response.json()["priority"] == "P4"


# --- when the asset changes ------------------------------------------------


def test_asset_criticality_change_reprioritises_open_incidents(client: TestClient) -> None:
    asset = make_asset(client, "crm", "low")
    incident = make_incident(client, "medium", asset_ids=[asset["id"]])
    assert incident["priority"] == "P3"

    client.patch(f"/assets/{asset['id']}", json={"criticality": "critical"})
    assert priority_of(client, incident["id"]) == "P2"

    client.patch(f"/assets/{asset['id']}", json={"criticality": "low"})
    assert priority_of(client, incident["id"]) == "P3"


def test_closed_incidents_are_not_reprioritised(client: TestClient) -> None:
    asset = make_asset(client, "crm", "low")
    incident = make_incident(client, "medium", asset_ids=[asset["id"]])
    close(client, incident["id"])

    client.patch(f"/assets/{asset['id']}", json={"criticality": "critical"})

    assert priority_of(client, incident["id"]) == "P3"  # congelado


def test_deleting_a_critical_asset_reprioritises_open_incidents(client: TestClient) -> None:
    payments = make_asset(client, "payments-db", "critical")
    incident = make_incident(client, "medium", asset_ids=[payments["id"]])
    assert incident["priority"] == "P2"

    assert client.delete(f"/assets/{payments['id']}").status_code == 204

    remaining = client.get(f"/incidents/{incident['id']}").json()
    assert remaining["priority"] == "P3"
    assert remaining["assets"] == []


def test_deleting_an_asset_keeps_closed_incident_priority(client: TestClient) -> None:
    payments = make_asset(client, "payments-db", "critical")
    incident = make_incident(client, "medium", asset_ids=[payments["id"]])
    close(client, incident["id"])

    assert client.delete(f"/assets/{payments['id']}").status_code == 204

    remaining = client.get(f"/incidents/{incident['id']}").json()
    assert remaining["priority"] == "P2"
    assert remaining["assets"] == []


# --- listing ---------------------------------------------------------------


def test_list_sorted_by_priority_then_newest(client: TestClient) -> None:
    make_incident(client, "low", title="low-1")
    make_incident(client, "critical", title="crit-1")
    make_incident(client, "medium", title="med-1")
    make_incident(client, "critical", title="crit-2")

    by_priority = client.get("/incidents", params={"sort": "priority"}).json()
    assert [i["title"] for i in by_priority] == ["crit-2", "crit-1", "med-1", "low-1"]

    newest = client.get("/incidents").json()
    assert [i["title"] for i in newest] == ["crit-2", "med-1", "crit-1", "low-1"]


def test_list_filters_by_priority_and_rejects_invalid_values(client: TestClient) -> None:
    make_incident(client, "critical", title="crit")
    make_incident(client, "low", title="low")

    p1 = client.get("/incidents", params={"priority": "P1"}).json()

    assert [i["title"] for i in p1] == ["crit"]
    assert client.get("/incidents", params={"priority": "P9"}).status_code == 422
    assert client.get("/incidents", params={"sort": "random"}).status_code == 422
