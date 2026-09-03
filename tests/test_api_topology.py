from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from kss.models.topology import Area, Line
from tests.helpers import persist_area_line_segment, persist_installation

JSONAPI = "application/vnd.api+json"


def test_get_topology_kss_only(client: TestClient, session: Session) -> None:
    installation = persist_installation(session)
    segment, line_id = persist_area_line_segment(session, installation)
    line = session.get(Line, line_id)
    assert line is not None
    area_id = max(line.versions, key=lambda item: item.last_modified).area_id
    area = session.get(Area, area_id)
    assert area is not None

    assert client.get("/api/v1/areas").status_code == 404
    spec = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/areas" not in spec
    assert "/api/kss/areas" in spec

    collection = client.get("/api/kss/areas")
    assert collection.status_code == 200
    assert JSONAPI in collection.headers["content-type"]
    item = collection.json()["data"][0]
    assert item["type"] == "area"
    assert item["id"] == str(area.id)
    assert item["attributes"]["title"] == "Bereich 1"
    assert item["attributes"]["kss:etsId"] == "A-1"
    assert item["attributes"]["kss:address"] == 1
    assert "lastModified" not in item["attributes"]

    single = client.get(f"/api/kss/areas/{area.id}")
    assert single.status_code == 200
    assert single.json()["data"]["attributes"]["kss:etsId"] == "A-1"

    lines = client.get("/api/kss/lines")
    assert lines.status_code == 200
    line_item = lines.json()["data"][0]
    assert line_item["id"] == str(line.id)
    assert line_item["attributes"]["kss:etsId"] == "L-1"
    assert line_item["attributes"]["kss:mediumType"] == "MT-0"
    assert line_item["relationships"]["area"]["data"] == {
        "type": "area",
        "id": str(area.id),
    }

    segments = client.get("/api/kss/segments")
    assert segments.status_code == 200
    segment_item = segments.json()["data"][0]
    assert segment_item["id"] == str(segment.id)
    assert segment_item["attributes"]["kss:etsId"] == "S-1"
    assert segment_item["relationships"]["line"]["data"] == {
        "type": "line",
        "id": str(line.id),
    }

    missing = client.get("/api/kss/areas/not-a-uuid")
    assert missing.status_code == 404
