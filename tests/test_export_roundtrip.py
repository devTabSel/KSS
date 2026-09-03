"""Export → empty DB → import → export must be identical."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from difflib import unified_diff
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from rdflib import Graph
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from kss.db import engine
from kss.models.base import Base
from kss.models.installation import Installation
from kss.models.trade import Trade
import kss.models  # noqa: F401
from kss.services.bus_bindings import upsert_bus_bindings_from_project
from kss.services.datapoints import upsert_datapoints_from_project
from kss.services.device_parts import (
    upsert_comm_object_datapoints_from_project,
    upsert_device_parts_from_project,
)
from kss.services.devices import upsert_devices_from_project
from kss.services.installations import upsert_installation_from_info
from kss.services.knxproj import parse_knxproj, project_info
from kss.services.knxproj_export import serialize_knxproj
from kss.services.locations import upsert_locations_from_project
from kss.services.master import upsert_master_catalog
from kss.services.snapshot import snapshot_installation
from kss.services.topology import upsert_topology_from_project
from kss.services.trades import upsert_trades_from_project
from kss.services.ttl import ingest_ttl
from kss.services.ttl_export import serialize_ttl
from tests.test_export import _seed

RT_SCHEMA = "kss_pytest_roundtrip"


@contextmanager
def empty_session() -> Generator[Session, None, None]:
    with engine.connect() as connection:
        connection.execute(text(f"DROP SCHEMA IF EXISTS {RT_SCHEMA} CASCADE"))
        connection.execute(text(f"CREATE SCHEMA {RT_SCHEMA}"))
        connection.commit()
        trans = connection.begin()
        connection.execute(text(f"SET LOCAL search_path TO {RT_SCHEMA}"))
        Base.metadata.create_all(bind=connection)
        factory = sessionmaker(
            bind=connection,
            join_transaction_mode="create_savepoint",
        )
        session = factory()
        try:
            yield session
            session.flush()
        finally:
            session.close()
            trans.rollback()
            connection.execute(text(f"DROP SCHEMA IF EXISTS {RT_SCHEMA} CASCADE"))
            connection.commit()


def _current_snap(session: Session):
    installation = session.scalars(select(Installation)).one()
    snap = snapshot_installation(session, installation.id, None)
    assert snap is not None
    return snap


def _ingest_knxproj(session: Session, path: Path) -> None:
    project = parse_knxproj(path)
    upsert_master_catalog(session, project.get("master_data"))
    result = upsert_installation_from_info(
        session,
        dict(project_info(project)),
        import_clock=datetime.now(UTC),
    )
    upsert_topology_from_project(
        session,
        result.installation,
        project,
        fallback_last_modified=result.version.last_modified,
    )
    upsert_locations_from_project(
        session,
        result.installation,
        project,
        fallback_last_modified=result.version.last_modified,
    )
    upsert_devices_from_project(
        session,
        result.installation,
        project,
        fallback_last_modified=result.version.last_modified,
    )
    upsert_device_parts_from_project(
        session,
        result.installation,
        project,
        fallback_last_modified=result.version.last_modified,
    )
    upsert_datapoints_from_project(
        session,
        result.installation,
        project,
        fallback_last_modified=result.version.last_modified,
    )
    upsert_comm_object_datapoints_from_project(
        session,
        result.installation,
        project,
        fallback_last_modified=result.version.last_modified,
    )
    upsert_bus_bindings_from_project(
        session,
        result.installation,
        project,
        fallback_last_modified=result.version.last_modified,
    )
    upsert_trades_from_project(
        session,
        result.installation,
        project,
        fallback_last_modified=result.version.last_modified,
    )
    session.flush()


def _ttl_ntriples(turtle: str) -> set[str]:
    graph = Graph()
    graph.parse(data=turtle, format="turtle")
    text = graph.serialize(format="nt")
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    return {line for line in text.splitlines() if line.strip()}


def _zip_members(payload: bytes) -> dict[str, bytes]:
    with ZipFile(BytesIO(payload)) as archive:
        return {name: archive.read(name) for name in sorted(archive.namelist())}


def _report_ttl(first: str, second: str) -> str:
    left = sorted(_ttl_ntriples(first))
    right = sorted(_ttl_ntriples(second))
    only_first = [line for line in left if line not in set(right)]
    only_second = [line for line in right if line not in set(left)]
    text_diff = "".join(
        unified_diff(
            first.splitlines(keepends=True),
            second.splitlines(keepends=True),
            fromfile="export1.ttl",
            tofile="export2.ttl",
            n=2,
        )
    )
    return (
        f"TTL roundtrip not identical.\n"
        f"only in first ({len(only_first)}):\n"
        + "\n".join(only_first[:40])
        + f"\n\nonly in second ({len(only_second)}):\n"
        + "\n".join(only_second[:40])
        + "\n\ntext diff (truncated):\n"
        + text_diff[:4000]
    )


def _report_zip(first: bytes, second: bytes) -> str:
    left = _zip_members(first)
    right = _zip_members(second)
    names_left, names_right = set(left), set(right)
    chunks: list[str] = []
    if names_left != names_right:
        chunks.append(
            f"zip members differ: only first {sorted(names_left - names_right)} "
            f"only second {sorted(names_right - names_left)}"
        )
    for name in sorted(names_left & names_right):
        if left[name] == right[name]:
            continue
        a = left[name].decode("utf-8", errors="replace")
        b = right[name].decode("utf-8", errors="replace")
        diff = "".join(
            unified_diff(
                a.splitlines(keepends=True),
                b.splitlines(keepends=True),
                fromfile=f"export1:{name}",
                tofile=f"export2:{name}",
                n=2,
            )
        )
        chunks.append(f"{name} differs:\n{diff[:4000]}")
    return "knxproj roundtrip not identical.\n" + "\n".join(chunks)


def test_ttl_export_import_export_identical(session: Session, tmp_path: Path) -> None:
    _seed(session)
    first = serialize_ttl(_current_snap(session))
    path = tmp_path / "first.ttl"
    path.write_text(first, encoding="utf-8")
    with empty_session() as other:
        ingest_ttl(other, path, import_clock=datetime.now(UTC))
        trades = other.scalars(select(Trade)).all()
        assert {row.ets_id for row in trades} == {"T-46"}
        second = serialize_ttl(_current_snap(other))
    if first != second:
        raise AssertionError(_report_ttl(first, second))


def test_knxproj_export_import_export_identical_less_info(
    session: Session, tmp_path: Path
) -> None:
    _seed(session)
    first = serialize_knxproj(_current_snap(session), less_info=True)
    path = tmp_path / "first.knxproj"
    path.write_bytes(first)
    with empty_session() as other:
        _ingest_knxproj(other, path)
        second = serialize_knxproj(_current_snap(other), less_info=True)
    if _zip_members(first) != _zip_members(second):
        raise AssertionError(_report_zip(first, second))


def test_knxproj_export_import_export_identical_more_info(
    session: Session, tmp_path: Path
) -> None:
    _seed(session)
    first = serialize_knxproj(_current_snap(session), less_info=False)
    path = tmp_path / "first.knxproj"
    path.write_bytes(first)
    with empty_session() as other:
        _ingest_knxproj(other, path)
        second = serialize_knxproj(_current_snap(other), less_info=False)
    if _zip_members(first) != _zip_members(second):
        raise AssertionError(_report_zip(first, second))
