from fastapi.testclient import TestClient


def make_incident(client: TestClient, **overrides) -> dict:
    payload = {"title": "Ransomware on file server", "severity": "critical", **overrides}
    response = client.post("/incidents", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def transition(client: TestClient, incident_id: int, to_status: str, **extra):
    return client.post(
        f"/incidents/{incident_id}/transitions", json={"to_status": to_status, **extra}
    )


def history(client: TestClient, incident_id: int) -> list[dict]:
    response = client.get(f"/incidents/{incident_id}/history")
    assert response.status_code == 200
    return response.json()


def test_full_lifecycle_records_every_step_in_the_audit_trail(client: TestClient) -> None:
    incident = make_incident(client)
    iid = incident["id"]

    for target in ("investigating", "mitigated", "resolved", "closed"):
        response = transition(client, iid, target, comment=f"moving to {target}")
        assert response.status_code == 200, response.text
        assert response.json()["status"] == target

    trail = history(client, iid)
    assert [(h["from_status"], h["to_status"]) for h in trail] == [
        (None, "open"),
        ("open", "investigating"),
        ("investigating", "mitigated"),
        ("mitigated", "resolved"),
        ("resolved", "closed"),
    ]
    assert trail[1]["comment"] == "moving to investigating"
    assert all(h["incident_id"] == iid and h["changed_at"] for h in trail)


def test_resolved_and_closed_timestamps_are_set(client: TestClient) -> None:
    iid = make_incident(client)["id"]
    for target in ("investigating", "mitigated"):
        transition(client, iid, target)
    assert client.get(f"/incidents/{iid}").json()["resolved_at"] is None

    resolved = transition(client, iid, "resolved").json()
    assert resolved["resolved_at"] is not None and resolved["closed_at"] is None

    closed = transition(client, iid, "closed").json()
    assert closed["closed_at"] is not None
    assert closed["resolved_at"] == resolved["resolved_at"]


def test_cannot_skip_states(client: TestClient) -> None:
    iid = make_incident(client)["id"]

    response = transition(client, iid, "closed")

    assert response.status_code == 409
    body = response.json()
    assert "open" in body["detail"] and "closed" in body["detail"]
    assert body["allowed_transitions"] == ["investigating"]


def test_rejected_transition_leaves_no_trace(client: TestClient) -> None:
    iid = make_incident(client)["id"]

    assert transition(client, iid, "resolved").status_code == 409

    assert client.get(f"/incidents/{iid}").json()["status"] == "open"
    assert len(history(client, iid)) == 1  # só o registo de criação


def test_transition_to_same_status_is_rejected(client: TestClient) -> None:
    iid = make_incident(client)["id"]

    assert transition(client, iid, "open").status_code == 409


def test_reopening_a_resolved_incident_clears_resolved_at(client: TestClient) -> None:
    iid = make_incident(client)["id"]
    for target in ("investigating", "mitigated", "resolved"):
        transition(client, iid, target)

    reopened = transition(client, iid, "investigating", comment="Attack resumed").json()

    assert reopened["status"] == "investigating"
    assert reopened["resolved_at"] is None
    assert history(client, iid)[-1]["comment"] == "Attack resumed"


def test_failed_mitigation_goes_back_to_investigating(client: TestClient) -> None:
    iid = make_incident(client)["id"]
    transition(client, iid, "investigating")
    transition(client, iid, "mitigated")

    assert transition(client, iid, "investigating").status_code == 200


def test_closed_incident_is_final(client: TestClient) -> None:
    iid = make_incident(client)["id"]
    for target in ("investigating", "mitigated", "resolved", "closed"):
        transition(client, iid, target)

    for target in ("open", "investigating", "mitigated", "resolved", "closed"):
        assert transition(client, iid, target).status_code == 409


def test_incident_exposes_allowed_transitions(client: TestClient) -> None:
    incident = make_incident(client)
    assert incident["allowed_transitions"] == ["investigating"]

    transition(client, incident["id"], "investigating")
    transition(client, incident["id"], "mitigated")

    current = client.get(f"/incidents/{incident['id']}").json()
    assert current["allowed_transitions"] == ["investigating", "resolved"]


def test_transition_validates_input(client: TestClient) -> None:
    iid = make_incident(client)["id"]
    url = f"/incidents/{iid}/transitions"

    assert client.post(url, json={}).status_code == 422
    assert client.post(url, json={"to_status": "on_fire"}).status_code == 422
    assert client.post(url, json={"to_status": "investigating", "comment": "x" * 2001}).status_code == 422


def test_transition_and_history_of_missing_incident_return_404(client: TestClient) -> None:
    assert transition(client, 424242, "investigating").status_code == 404
    assert client.get("/incidents/424242/history").status_code == 404


def test_new_incident_history_has_creation_entry(client: TestClient) -> None:
    iid = make_incident(client)["id"]

    trail = history(client, iid)

    assert len(trail) == 1
    assert trail[0]["from_status"] is None
    assert trail[0]["to_status"] == "open"
    assert trail[0]["comment"] == "Incident created"
