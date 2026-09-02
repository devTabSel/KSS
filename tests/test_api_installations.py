from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from kss.db import get_session
from kss.main import app
from tests.helpers import persist_installation
from tests.wa53h10 import (
    ETS6_FREE_KNXPROJ,
    WA53H10_ETS_ID,
    WA53H10_GUID,
    WA53H10_KNXPROJ,
    write_wa53h10_installation_knxproj,
)

import pytest

JSONAPI = "application/vnd.api+json"


def _kss_keys(attributes: dict) -> set[str]:
    return {key for key in attributes if key.startswith("kss:")}


def test_empty_collection_has_pagination_meta(client: TestClient) -> None:
    response = client.get("/api/v1/installations")
    assert response.status_code == 200
    assert JSONAPI in response.headers["content-type"]
    body = response.json()
    assert body["data"] == []
    assert body["meta"]["collection"] == {"number": 0, "size": 0, "total": 0}


def test_get_v1_omits_kss_attributes(client: TestClient, session: Session) -> None:
    installation = persist_installation(session, title="WA53H10")
    installation.project_guid = UUID(WA53H10_GUID)
    session.flush()

    collection = client.get("/api/v1/installations")
    assert collection.status_code == 200
    item = collection.json()["data"][0]
    assert item["type"] == "installation"
    assert item["id"] == str(installation.id)
    assert item["attributes"]["title"] == "WA53H10"
    assert _kss_keys(item["attributes"]) == set()

    single = client.get(f"/api/v1/installations/{installation.id}")
    assert single.status_code == 200
    assert _kss_keys(single.json()["data"]["attributes"]) == set()


def test_get_kss_includes_kss_attributes(client: TestClient, session: Session) -> None:
    installation = persist_installation(session, title="WA53H10")
    installation.project_guid = UUID(WA53H10_GUID)
    session.flush()

    collection = client.get("/api/kss/installations")
    assert collection.status_code == 200
    collection_item = collection.json()["data"][0]
    assert collection_item["attributes"]["title"] == "WA53H10"
    assert "kss:projectGuid" in collection_item["attributes"]

    response = client.get(f"/api/kss/installations/{installation.id}")
    assert response.status_code == 200
    attributes = response.json()["data"]["attributes"]
    assert attributes["title"] == "WA53H10"
    assert attributes["kss:etsId"] == WA53H10_ETS_ID
    assert attributes["kss:projectGuid"] == WA53H10_GUID
    assert attributes["kss:installationIndex"] == 0
    assert attributes["kss:groupAddressStyle"] == "ThreeLevel"
    assert "kss:lastImport" in attributes


def test_v1_rejects_post_and_patch(client: TestClient) -> None:
    assert client.post("/api/v1/installations", json={}).status_code == 405
    assert client.patch("/api/v1/installations", json={}).status_code == 405
    spec = client.get("/openapi.json").json()["paths"]
    assert "patch" not in spec.get("/api/v1/installations", {})
    assert "patch" in spec.get("/api/kss/installations", {})


def test_patch_unknown_format_is_422(client: TestClient) -> None:
    response = client.patch(
        "/api/kss/installations",
        files={"file": ("notes.txt", b"not a knxproj", "text/plain")},
    )
    assert response.status_code == 422
    assert JSONAPI in response.headers["content-type"]
    errors = response.json()["errors"]
    assert errors[0]["status"] == "422"
    assert "unsupported file format" in errors[0]["detail"]
    assert ".knxproj" in errors[0]["detail"]
    assert ".ttl" in errors[0]["detail"]


def test_patch_ttl_is_501(client: TestClient) -> None:
    response = client.patch(
        "/api/kss/installations",
        files={"file": ("project.ttl", b"@prefix knx: <http://example/> .", "text/turtle")},
    )
    assert response.status_code == 501
    assert JSONAPI in response.headers["content-type"]
    error = response.json()["errors"][0]
    assert error["status"] == "501"
    assert error["title"] == "Not Implemented"
    assert ".ttl" in error["detail"]
    assert ".knxproj" in error["detail"]


def test_patch_ets_id_conflict_is_422(
    client: TestClient, session: Session, monkeypatch
) -> None:
    persist_installation(session, ets_id=WA53H10_ETS_ID)
    session.flush()
    info = {
        "project_id": "P-FFFF",
        "name": "other",
        "last_modified": "2026-08-07T08:28:38Z",
        "group_address_style": "ThreeLevel",
        "guid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "schema_version": "23",
        "installation_index": 0,
        "ets_id": WA53H10_ETS_ID,
        "completion_status": "Editing",
        "comment": None,
        "master_data_version": 1,
        "project_number": None,
        "contract_number": None,
        "project_type": None,
    }
    monkeypatch.setattr(
        "kss.api.installations.parse_knxproj",
        lambda path, password=None: {"info": info},
    )
    monkeypatch.setattr(
        "kss.api.installations.project_info",
        lambda project: project["info"],
    )
    response = client.patch(
        "/api/kss/installations",
        files={"file": ("WA53H10.knxproj", b"stub", "application/octet-stream")},
    )
    assert response.status_code == 422
    assert JSONAPI in response.headers["content-type"]
    assert response.json()["errors"][0]["status"] == "422"
    assert "ets id" in response.json()["errors"][0]["detail"]


def test_patch_parser_bug_is_jsonapi_500(session: Session, monkeypatch) -> None:
    def boom(path, password=None):
        del path, password
        raise RuntimeError("parser bug")

    monkeypatch.setattr("kss.api.installations.parse_knxproj", boom)

    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.patch(
                "/api/kss/installations",
                files={
                    "file": ("WA53H10.knxproj", b"stub", "application/octet-stream")
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert JSONAPI in response.headers["content-type"]
    error = response.json()["errors"][0]
    assert error["status"] == "500"
    assert error["title"] == "Internal Server Error"
    assert "parser bug" not in error["detail"]


def test_patch_create_then_noop_is_201_then_204(
    client: TestClient, monkeypatch
) -> None:
    guid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    info = {
        "project_id": "P-FFFF",
        "name": "other",
        "last_modified": "2026-08-07T08:28:38Z",
        "group_address_style": "ThreeLevel",
        "guid": guid,
        "schema_version": "23",
        "installation_index": 0,
        "ets_id": "P-FFFF-0",
        "completion_status": "Editing",
        "comment": None,
        "master_data_version": 1,
        "project_number": None,
        "contract_number": None,
        "project_type": None,
    }
    monkeypatch.setattr(
        "kss.api.installations.parse_knxproj",
        lambda path, password=None: {"info": info},
    )
    monkeypatch.setattr(
        "kss.api.installations.project_info",
        lambda project: project["info"],
    )
    files = {"file": ("other.knxproj", b"stub", "application/octet-stream")}

    created = client.patch("/api/kss/installations", files=files)
    assert created.status_code == 201
    assert created.content == b""

    collection = client.get("/api/kss/installations")
    item = next(
        row
        for row in collection.json()["data"]
        if row["attributes"]["kss:projectGuid"] == guid
    )
    assert item["attributes"]["title"] == "other"

    again = client.patch("/api/kss/installations", files=files)
    assert again.status_code == 204
    assert again.content == b""


def test_patch_schema_22_is_422(client: TestClient) -> None:
    payload = ETS6_FREE_KNXPROJ.read_bytes()
    response = client.patch(
        "/api/kss/installations",
        files={"file": ("ets6_free.knxproj", payload, "application/octet-stream")},
    )
    assert response.status_code == 422
    assert "below 23" in response.json()["errors"][0]["detail"]


@pytest.mark.skipif(not WA53H10_KNXPROJ.is_file(), reason="WA53H10.knxproj missing")
def test_patch_wa53h10_creates_and_is_idempotent(
    client: TestClient, tmp_path
) -> None:
    knxproj = write_wa53h10_installation_knxproj(tmp_path / "WA53H10.knxproj")
    payload = knxproj.read_bytes()
    files = {"file": ("WA53H10.knxproj", payload, "application/octet-stream")}

    created = client.patch("/api/kss/installations", files=files)
    assert created.status_code == 201
    assert created.content == b""

    collection = client.get("/api/kss/installations")
    data = next(
        item
        for item in collection.json()["data"]
        if item["attributes"]["kss:projectGuid"] == WA53H10_GUID
    )
    installation_id = data["id"]
    attributes = data["attributes"]
    assert attributes["title"] == "WA53H10"
    assert attributes["state"] == "Editing"
    assert attributes["comment"].startswith(r"{\rtf1")
    assert attributes["kss:etsId"] == WA53H10_ETS_ID
    assert attributes["kss:projectGuid"] == WA53H10_GUID
    assert attributes["kss:installationIndex"] == 0
    assert attributes["kss:groupAddressStyle"] == "ThreeLevel"
    assert attributes["kss:masterDataVersion"] == 285
    assert attributes["kss:projectType"] == "Family House"
    assert "lastModified" in attributes
    assert "kss:projectType" in attributes
    assert "contractNumber" not in attributes
    assert "projectInstallationNumber" not in attributes

    v1 = client.get(f"/api/v1/installations/{installation_id}")
    assert v1.status_code == 200
    v1_attributes = v1.json()["data"]["attributes"]
    assert v1_attributes["title"] == "WA53H10"
    assert _kss_keys(v1_attributes) == set()
    assert "kss:projectType" not in v1_attributes

    again = client.patch("/api/kss/installations", files=files)
    assert again.status_code == 204
    assert again.content == b""
