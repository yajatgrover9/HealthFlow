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
