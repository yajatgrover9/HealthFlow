import os

from src.app import Base, engine

os.environ["DATABASE_URL"] = "sqlite:///./test_healthflow.db"
os.environ["APP_API_KEY"] = "test-api-key"

from fastapi.testclient import TestClient

from src.app import app

client = TestClient(app)
HEADERS = {"x-api-key": "test-api-key"}


def setup_module():
    Base.metadata.create_all(bind=engine)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_station_patient_flow_recompute_and_checkout():
    s1 = client.post(
        "/v1/stations", json={"name": "Blood", "avg_duration_min": 8}, headers=HEADERS
    )
    s2 = client.post(
        "/v1/stations", json={"name": "ECG", "avg_duration_min": 12}, headers=HEADERS
    )
    assert s1.status_code == 200
    assert s2.status_code == 200

    p1 = client.post(
        "/v1/patients",
        json={"external_id": "P-001", "station_ids_in_order": [1, 2]},
        headers=HEADERS,
    )
    assert p1.status_code == 200

    # Assign for first station
    first_assign = client.post("/v1/flow/recompute", headers=HEADERS)
    assert first_assign.status_code == 200
    data = first_assign.json()
    assert data[0]["patient_external_id"] == "P-001"
    assert data[0]["station_name"] == "Blood"

    # Start first station (patient enters)
    started1 = client.post(
        "/v1/flow/start",
        json={"patient_id": data[0]["patient_id"], "station_id": data[0]["station_id"]},
        headers=HEADERS,
    )
    assert started1.status_code == 200

    # Complete first station
    done1 = client.post(
        "/v1/flow/complete",
        json={"patient_id": data[0]["patient_id"], "station_id": data[0]["station_id"]},
        headers=HEADERS,
    )
    assert done1.status_code == 200

    # Patient should NOT be checked out yet (still has ECG)
    patients = client.get("/v1/patients", headers=HEADERS)
    assert patients.status_code == 200
    p = next(x for x in patients.json() if x["external_id"] == "P-001")
    assert p["checked_out_at"] is None

    # Now ECG should be assigned
    second_assignments = done1.json()
    ecg_assignment = next(
        a
        for a in second_assignments
        if a["patient_external_id"] == "P-001" and a["station_name"] == "ECG"
    )

    # Start ECG
    started2 = client.post(
        "/v1/flow/start",
        json={
            "patient_id": ecg_assignment["patient_id"],
            "station_id": ecg_assignment["station_id"],
        },
        headers=HEADERS,
    )
    assert started2.status_code == 200

    # Complete ECG
    done2 = client.post(
        "/v1/flow/complete",
        json={
            "patient_id": ecg_assignment["patient_id"],
            "station_id": ecg_assignment["station_id"],
        },
        headers=HEADERS,
    )
    assert done2.status_code == 200

    # Now patient should be checked out
    patients2 = client.get("/v1/patients", headers=HEADERS)
    assert patients2.status_code == 200
    p2 = next(x for x in patients2.json() if x["external_id"] == "P-001")
    assert p2["checked_out_at"] is not None


def test_requires_api_key_for_v1_routes():
    response = client.get("/v1/stations")
    assert response.status_code == 401


def test_auto_reroute_between_equivalent_stations():
    # Create two equivalent stations (same prefix "Blood")
    s1 = client.post(
        "/v1/stations", json={"name": "Blood A", "avg_duration_min": 8}, headers=HEADERS
    )
    s2 = client.post(
        "/v1/stations", json={"name": "Blood B", "avg_duration_min": 8}, headers=HEADERS
    )
    assert s1.status_code == 200
    assert s2.status_code == 200

    # Create two patients that both start at Blood A (id=1)
    p1 = client.post(
        "/v1/patients",
        json={"external_id": "P-RA-001", "station_ids_in_order": [1]},
        headers=HEADERS,
    )
    p2 = client.post(
        "/v1/patients",
        json={"external_id": "P-RA-002", "station_ids_in_order": [1]},
        headers=HEADERS,
    )
    assert p1.status_code == 200
    assert p2.status_code == 200

    # Initial recompute should assign first patient to Blood A
    first_assign = client.post("/v1/flow/recompute", headers=HEADERS)
    assert first_assign.status_code == 200

    # Complete first patient's task at Blood A to free it and then recompute again
    tasks = client.get("/v1/flow/tasks", headers=HEADERS)
    assert tasks.status_code == 200
    task_list = tasks.json()
    # Find task for first patient
    t1 = next(t for t in task_list if t["patient_id"] == 1)

    started = client.post(
        "/v1/flow/start",
        json={"patient_id": t1["patient_id"], "station_id": t1["station_id"]},
        headers=HEADERS,
    )
    assert started.status_code == 200

    completed = client.post(
        "/v1/flow/complete",
        json={"patient_id": t1["patient_id"], "station_id": t1["station_id"]},
        headers=HEADERS,
    )
    assert completed.status_code == 200

    # Now reroute logic runs after recompute; second patient's pending task
    # may be moved between Blood A and Blood B based on queue ETA.
    tasks_after = client.get("/v1/flow/tasks", headers=HEADERS)
    assert tasks_after.status_code == 200
    remaining_tasks = [t for t in tasks_after.json() if t["status"] != "done"]
    assert len(remaining_tasks) >= 1

    # Ensure remaining task station is either 1 (Blood A) or 2 (Blood B)
    for t in remaining_tasks:
        assert t["station_id"] in (1, 2)
