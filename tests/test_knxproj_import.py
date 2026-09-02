from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from xknxproject.exceptions import UnexpectedFileContent

from kss.models.installation import Installation, InstallationVersion
from kss.services.installations import upsert_installation_from_info
from kss.services.knxproj import KnxprojImportError, parse_knxproj
from tests.helpers import persist_installation
from tests.wa53h10 import WA53H10_ETS_ID, WA53H10_GUID, WA53H10_INFO

import pytest


def _import_clock() -> datetime:
    return datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def test_creates_installation_from_wa53h10_info(session: Session) -> None:
    clock = _import_clock()
    result = upsert_installation_from_info(
        session, dict(WA53H10_INFO), import_clock=clock
    )
    assert result.created is True
    assert result.versioned is True
    assert result.installation.ets_id == "P-040E-0"
    assert result.version.group_address_style == "ThreeLevel"
    assert str(result.installation.project_guid) == WA53H10_GUID
    assert result.version.title == "WA53H10"
    assert result.version.completion_status == "Editing"
    assert result.version.master_data_version == 285
    assert result.version.comment == WA53H10_INFO["comment"]
    assert result.version.contract_number is None
    assert result.version.project_installation_number is None
    assert result.version.project_type == "Family House"
    assert result.version.last_modified is not None
    assert result.installation.last_import == clock


def test_identical_reimport_updates_last_import_without_versioning(session: Session) -> None:
    first_clock = _import_clock()
    first = upsert_installation_from_info(
        session, dict(WA53H10_INFO), import_clock=first_clock
    )
    second_clock = datetime(2026, 9, 1, 13, 0, tzinfo=UTC)
    second = upsert_installation_from_info(
        session,
        dict(WA53H10_INFO),
        import_clock=second_clock,
    )
    assert second.created is False
    assert second.versioned is False
    assert second.installation.id == first.installation.id
    count = session.scalar(select(func.count()).select_from(InstallationVersion))
    assert count == 1
    assert second.installation.last_import == second_clock


def test_last_modified_alone_does_not_version(session: Session) -> None:
    upsert_installation_from_info(
        session, dict(WA53H10_INFO), import_clock=_import_clock()
    )
    changed = dict(WA53H10_INFO)
    changed["last_modified"] = "2026-08-08T00:00:00Z"
    result = upsert_installation_from_info(
        session, changed, import_clock=_import_clock()
    )
    assert result.versioned is False
    assert session.scalar(select(func.count()).select_from(InstallationVersion)) == 1


def test_title_change_with_new_last_modified_creates_version(session: Session) -> None:
    first = upsert_installation_from_info(
        session, dict(WA53H10_INFO), import_clock=_import_clock()
    )
    changed = dict(WA53H10_INFO)
    changed["name"] = "WA53H10 umbenannt"
    changed["last_modified"] = "2026-08-08T00:00:00Z"
    result = upsert_installation_from_info(
        session, changed, import_clock=_import_clock()
    )
    assert result.created is False
    assert result.versioned is True
    assert result.installation.id == first.installation.id
    versions = session.scalars(select(InstallationVersion)).all()
    assert len(versions) == 2
    assert result.version.title == "WA53H10 umbenannt"


def test_same_last_modified_does_not_insert_even_if_title_differs(session: Session) -> None:
    upsert_installation_from_info(
        session, dict(WA53H10_INFO), import_clock=_import_clock()
    )
    changed = dict(WA53H10_INFO)
    changed["name"] = "ignored because same LastModified"
    result = upsert_installation_from_info(
        session, changed, import_clock=_import_clock()
    )
    assert result.versioned is False
    assert result.version.title == "WA53H10"
    assert session.scalar(select(func.count()).select_from(InstallationVersion)) == 1


def test_identity_fields_are_not_rewritten(session: Session) -> None:
    first = upsert_installation_from_info(
        session, dict(WA53H10_INFO), import_clock=_import_clock()
    )
    changed = dict(WA53H10_INFO)
    changed["ets_id"] = "P-FFFF-0"
    changed["group_address_style"] = "Free"
    changed["name"] = "WA53H10 umbenannt"
    changed["last_modified"] = "2026-08-08T00:00:00Z"
    result = upsert_installation_from_info(
        session, changed, import_clock=_import_clock()
    )
    session.refresh(first.installation)
    assert first.installation.ets_id == "P-040E-0"
    assert result.version.group_address_style == "Free"
    assert result.installation.id == first.installation.id


def test_schema_below_23_is_rejected(session: Session) -> None:
    info = dict(WA53H10_INFO)
    info["schema_version"] = "22"
    with pytest.raises(KnxprojImportError, match="below 23"):
        upsert_installation_from_info(session, info, import_clock=_import_clock())
    assert session.scalar(select(func.count()).select_from(Installation)) == 0


def test_project_type_change_with_new_last_modified_creates_version(session: Session) -> None:
    first = upsert_installation_from_info(
        session, dict(WA53H10_INFO), import_clock=_import_clock()
    )
    changed = dict(WA53H10_INFO)
    changed["project_type"] = "Office Building"
    changed["last_modified"] = "2026-08-08T00:00:00Z"
    result = upsert_installation_from_info(
        session, changed, import_clock=_import_clock()
    )
    assert result.created is False
    assert result.versioned is True
    assert result.installation.id == first.installation.id
    assert result.version.project_type == "Office Building"
    assert session.scalar(select(func.count()).select_from(InstallationVersion)) == 2


def test_unknown_project_type_is_rejected(session: Session) -> None:
    info = dict(WA53H10_INFO)
    info["project_type"] = "Familienhaus"
    with pytest.raises(KnxprojImportError, match="unsupported project type"):
        upsert_installation_from_info(session, info, import_clock=_import_clock())
    assert session.scalar(select(func.count()).select_from(Installation)) == 0


def test_duplicate_ets_id_is_rejected(session: Session) -> None:
    persist_installation(session, ets_id=WA53H10_ETS_ID)
    session.flush()
    info = dict(WA53H10_INFO)
    info["guid"] = str(uuid4())
    with pytest.raises(KnxprojImportError, match="ets id already exists"):
        upsert_installation_from_info(session, info, import_clock=_import_clock())


def test_parse_xknx_errors_become_import_errors(monkeypatch, tmp_path) -> None:
    path = tmp_path / "broken.knxproj"
    path.write_bytes(b"not a zip")

    class Boom:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        def parse(self, combine: bool = True) -> dict:
            del combine
            raise UnexpectedFileContent("bad archive")

    monkeypatch.setattr("kss.services.knxproj.XKNXProj", Boom)
    with pytest.raises(KnxprojImportError, match="bad archive"):
        parse_knxproj(path)


def test_parse_unexpected_errors_propagate(monkeypatch, tmp_path) -> None:
    path = tmp_path / "broken.knxproj"
    path.write_bytes(b"not a zip")

    class Boom:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        def parse(self, combine: bool = True) -> dict:
            del combine
            raise RuntimeError("parser bug")

    monkeypatch.setattr("kss.services.knxproj.XKNXProj", Boom)
    with pytest.raises(RuntimeError, match="parser bug"):
        parse_knxproj(path)
