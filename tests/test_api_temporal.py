from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from kss.api.flavor import at_path_token
from kss.models.installation import InstallationVersion
from kss.services.knxproj_export import TURTLE_MEDIA_TYPE
from kss.services.temporal import resolve_version, version_at
from tests.helpers import at, persist_device, persist_installation, persist_location


def _kss(at_value, *parts: str) -> str:
    return "/api/kss/" + "/".join((at_path_token(at_value), *parts))


def test_resolve_version_assumes_first_after_t() -> None:
    class Row:
        def __init__(self, hour: int) -> None:
            self.last_modified = at(hour)

    rows = [Row(0), Row(2)]
    before = datetime(2025, 12, 31, tzinfo=UTC)
    assumed = resolve_version(rows, before)
    assert assumed is not None
    assert assumed.assumed
    assert assumed.row.last_modified == at(0)
    exact = resolve_version(rows, at(1))
    assert exact is not None
    assert not exact.assumed
    assert exact.row.last_modified == at(0)
    assert version_at(rows, before) is None


def test_v1_is_always_current(client: TestClient, session: Session) -> None:
    installation = persist_installation(session, title="first", last_modified=at(0))
    session.add(
        InstallationVersion(
            installation_id=installation.id,
            title="later",
            last_modified=at(2),
            group_address_style="ThreeLevel",
        )
    )
    session.flush()
    response = client.get(f"/api/v1/installations/{installation.id}")
    assert response.status_code == 200
    assert response.json()["data"]["attributes"]["title"] == "later"
    assert "resolution" not in response.headers


def test_kss_current_is_exact(client: TestClient, session: Session) -> None:
    installation = persist_installation(session)
    response = client.get(f"/api/kss/installations/{installation.id}")
    assert response.status_code == 200
    assert response.headers["resolution"] == "exact"
    assert response.json()["data"]["attributes"]["title"] == "WA53H10"


def test_query_at_is_ignored(client: TestClient, session: Session) -> None:
    installation = persist_installation(session, title="first", last_modified=at(0))
    session.add(
        InstallationVersion(
            installation_id=installation.id,
            title="later",
            last_modified=at(2),
            group_address_style="ThreeLevel",
        )
    )
    session.flush()
    response = client.get(
        f"/api/kss/installations/{installation.id}",
        params={"at": "2026-01-01T01:00:00Z"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["attributes"]["title"] == "later"


def test_timed_item_and_collection(client: TestClient, session: Session) -> None:
    installation = persist_installation(session, title="first", last_modified=at(0))
    session.add(
        InstallationVersion(
            installation_id=installation.id,
            title="later",
            last_modified=at(2),
            group_address_style="ThreeLevel",
        )
    )
    early_device = persist_device(
        session, installation, title="old", ets_id="DI-1", last_modified=at(0)
    )
    persist_device(
        session, installation, title="new", ets_id="DI-2", last_modified=at(3)
    )
    session.flush()

    timed = client.get(_kss(at(1), "installations", str(installation.id)))
    assert timed.status_code == 200
    assert timed.headers["resolution"] == "exact"
    assert timed.json()["data"]["attributes"]["title"] == "first"

    devices = client.get(_kss(at(1), "devices"))
    assert devices.status_code == 200
    assert devices.headers["resolution"] == "assumed"
    titles = {item["attributes"]["title"] for item in devices.json()["data"]}
    assert titles == {"old", "new"}

    exact_devices = client.get(
        _kss(at(1), "devices"),
        headers={"resolution": "exact"},
    )
    assert exact_devices.status_code == 200
    assert exact_devices.headers["resolution"] == "exact"
    exact_titles = {
        item["attributes"]["title"] for item in exact_devices.json()["data"]
    }
    assert exact_titles == {"old"}

    future_item = client.get(_kss(at(1), "devices", str(early_device.id)))
    assert future_item.json()["data"]["attributes"]["title"] == "old"


def test_timed_assumed_item_and_nested(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session, last_modified=at(2))
    location = persist_location(
        session, installation, title="room", last_modified=at(2)
    )
    device = persist_device(
        session,
        installation,
        title="late",
        last_modified=at(2),
        location_id=location.id,
    )
    session.flush()

    before = at(0)
    item = client.get(_kss(before, "installations", str(installation.id)))
    assert item.status_code == 200
    assert item.headers["resolution"] == "assumed"
    assert item.json()["data"]["attributes"]["title"] == "WA53H10"

    collection = client.get(_kss(before, "devices"))
    assert collection.status_code == 200
    assert collection.headers["resolution"] == "assumed"
    assert collection.json()["data"][0]["id"] == str(device.id)

    nested = client.get(_kss(before, "locations", str(location.id), "devices"))
    assert nested.status_code == 200
    assert nested.headers["resolution"] == "assumed"
    assert nested.json()["data"][0]["id"] == str(device.id)
    assert nested.json()["data"][0]["attributes"]["title"] == "late"
    href = nested.json()["data"][0]["relationships"]["deviceLocation"]["links"][
        "related"
    ]
    assert href.startswith(f"/api/kss/{at_path_token(before)}/devices/")

    exact_item = client.get(
        _kss(before, "installations", str(installation.id)),
        headers={"resolution": "exact"},
    )
    assert exact_item.status_code == 404
    assert exact_item.headers["resolution"] == "exact"

    exact_collection = client.get(
        _kss(before, "devices"),
        headers={"resolution": "exact"},
    )
    assert exact_collection.status_code == 200
    assert exact_collection.json()["data"] == []
    assert exact_collection.headers["resolution"] == "exact"

    exact_nested = client.get(
        _kss(before, "locations", str(location.id), "devices"),
        headers={"resolution": "exact"},
    )
    assert exact_nested.status_code == 404
    assert exact_nested.headers["resolution"] == "exact"


def test_timed_invalid_at_is_422(client: TestClient, session: Session) -> None:
    installation = persist_installation(session)
    response = client.get(
        f"/api/kss/not-a-date/installations/{installation.id}"
    )
    assert response.status_code == 422


def test_timed_ttl_accept(client: TestClient, session: Session) -> None:
    installation = persist_installation(session, title="first", last_modified=at(0))
    session.add(
        InstallationVersion(
            installation_id=installation.id,
            title="later",
            last_modified=at(2),
            group_address_style="ThreeLevel",
        )
    )
    session.flush()
    ttl = client.get(
        _kss(at(1), "installations", str(installation.id)),
        headers={"Accept": TURTLE_MEDIA_TYPE},
    )
    assert ttl.status_code == 200
    assert TURTLE_MEDIA_TYPE in ttl.headers["content-type"]
    assert ttl.headers["resolution"] == "exact"
    assert "first" in ttl.text
    assert "later" not in ttl.text


def test_timed_ttl_assumes_future_package(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session, title="first", last_modified=at(0))
    persist_device(
        session, installation, title="late-device", ets_id="DI-9", last_modified=at(2)
    )
    session.flush()
    ttl = client.get(
        _kss(at(1), "installations", str(installation.id)),
        headers={"Accept": TURTLE_MEDIA_TYPE},
    )
    assert ttl.status_code == 200
    assert ttl.headers["resolution"] == "assumed"
    assert "late-device" in ttl.text

    exact_ttl = client.get(
        _kss(at(1), "installations", str(installation.id)),
        headers={"Accept": TURTLE_MEDIA_TYPE, "resolution": "exact"},
    )
    assert exact_ttl.status_code == 200
    assert exact_ttl.headers["resolution"] == "exact"
    assert "late-device" not in exact_ttl.text


def test_timed_invalid_resolution_is_422(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    response = client.get(
        _kss(at(1), "installations", str(installation.id)),
        headers={"resolution": "exakt"},
    )
    assert response.status_code == 422
