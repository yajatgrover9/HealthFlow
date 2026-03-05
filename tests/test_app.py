import os

from app.db.db import Base, engine

os.environ["DATABASE_URL"] = "sqlite:///./test_healthflow.db"
os.environ["APP_API_KEY"] = "test-api-key"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HEADERS = {"x-api-key": "test-api-key"}


def setup_module():
    Base.metadata.create_all(bind=engine)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_station_patient_flow_recompute():
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
    p2 = client.post(
        "/v1/patients",
        json={"external_id": "P-002", "station_ids_in_order": [1, 2]},
        headers=HEADERS,
    )
    assert p1.status_code == 200
    assert p2.status_code == 200

    first_assign = client.post("/v1/flow/recompute", headers=HEADERS)
    assert first_assign.status_code == 200
    data = first_assign.json()
    assert len(data) >= 1
    assert data[0]["patient_external_id"] == "P-001"
    assert data[0]["station_name"] == "Blood"

    done = client.post(
        "/v1/flow/complete", json={"task_id": data[0]["task_id"]}, headers=HEADERS
    )
    assert done.status_code == 200
    second = done.json()

    stations = {(a["patient_external_id"], a["station_name"]) for a in second}
    assert ("P-001", "ECG") in stations


def test_requires_api_key_for_v1_routes():
    response = client.get("/v1/stations")
    assert response.status_code == 401
