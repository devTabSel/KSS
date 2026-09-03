"""Parse ETS Semantic Export (Turtle) and upsert into the KSS model.

Identity join is ``project_guid`` + ``ets_id`` (TTL fragment). Does not call
``upsert_installation_from_info`` (schema ≥ 23 and would NULL knxproj-only
fields). Topology, trades, channels, COs, BUS, GroupRange and ``prj:Site``
are not persisted. Missing entities are not unlinked.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from rdflib import Graph, Literal, OWL, RDF, URIRef, XSD
from rdflib.term import Node
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from kss.models.constants import COMPLETION_STATUS_VALUES, LOCATION_TYPE_VALUES
from kss.models.datapoint import Datapoint, DatapointVersion
from kss.models.device import Device, DeviceVersion
from kss.models.installation import Installation, InstallationVersion
from kss.models.location import Function, FunctionDatapoint, FunctionVersion, Location, LocationVersion
from kss.services.datapoints import DATAPOINT_SEMANTIC_FIELDS, FUNCTION_DATAPOINT_SEMANTIC_FIELDS
from kss.services.devices import DEVICE_SEMANTIC_FIELDS
from kss.services.installations import SEMANTIC_FIELDS as INSTALLATION_SEMANTIC_FIELDS
from kss.services.installations import UpsertResult
from kss.services.knxproj import parse_ets_datetime
from kss.services.locations import FUNCTION_SEMANTIC_FIELDS, LOCATION_SEMANTIC_FIELDS

KNOWN_PREFIXES = {
    "core": "http://schema.knx.org/2023/en50090-6-2/core#",
    "loc": "http://schema.knx.org/2023/en50090-6-2/loc#",
    "knx": "http://schema.knx.org/2020/ontology/knx#",
    "mac": "http://schema.knx.org/2020/ontology/mac#",
    "tag": "http://schema.knx.org/2023/en50090-6-2/tag#",
    "dct": "http://purl.org/dc/terms/",
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}

PREFIX_LINE = re.compile(r"^@prefix\s+(\w+):\s+<([^>]+)>\s*\.\s*$")
COL0_CURIE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):")
GUID_IN_NS = re.compile(
    r"http://iot\.knx\.org/"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})#"
)
DEVICE_ETS = re.compile(r"^DI-\d+$")
LOCATION_ETS = re.compile(r"^BP-\d+$")
FUNCTION_ETS = re.compile(r"^F-\d+$")
DATAPOINT_ETS = re.compile(r"^GA-\d+$")

LOC_CHILD_PREDICATES = (
    "hasFloor",
    "hasRoom",
    "hasSpace",
    "hasLocation",
    "hasBuilding",
)
LOC_TYPE_TO_XSD = {
    "Building": "Building",
    "Floor": "Floor",
    "Room": "Room",
    "Space": "BuildingPart",
    "DistributionBoard": "DistributionBoard",
    "Stairway": "Stairway",
    "Corridor": "Corridor",
    "Area": "Area",
    "Ground": "Ground",
    "Segment": "Segment",
}

INSTALLATION_PRESERVE_FIELDS = (
    "contract_number",
    "project_installation_number",
    "project_type",
    "master_data_version",
    "schema_version",
    "created_by",
    "ip_routing_backbone_key",
    "bcu_key",
    "group_address_style",
)
LOCATION_PRESERVE_FIELDS = ("default_line_id",)
DEVICE_LOADED_FIELDS = frozenset(
    {
        "communication_part_loaded",
        "individual_address_loaded",
        "application_program_loaded",
        "parameters_loaded",
        "medium_config_loaded",
    }
)
DEVICE_PRESERVE_FIELDS = (
    "communication_part_loaded",
    "individual_address_loaded",
    "application_program_loaded",
    "parameters_loaded",
    "medium_config_loaded",
    "segment_id",
)
DATAPOINT_PRESERVE_FIELDS = ("datapoint_subtype_ets_id", "group_range_id")
TTL_DEVICE_SEMANTIC_FIELDS = DEVICE_SEMANTIC_FIELDS + (
    "assigned_trade",
    "operates_for_trade",
)
NAMED_INDIVIDUAL = str(OWL.NamedIndividual)


class TtlImportError(ValueError):
    """Rejected TTL ingest (parse or mapping)."""


@dataclass
class ParsedTtl:
    project_guid: UUID
    prj_ns: str
    graph: Graph
    prefixes: dict[str, str]
    individuals: dict[str, URIRef]
    installation_ets_id: str
    installation_subject: URIRef


def parse_ttl(path: Path) -> ParsedTtl:
    """Parse ``prj:`` individuals (before the ontology dump) into a graph."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TtlImportError("unreadable turtle") from exc
    if text.startswith("\ufeff"):
        text = text[1:]
    prefixes, chunk = _instance_turtle(text)
    graph = Graph()
    try:
        graph.parse(data=chunk, format="turtle")
    except Exception as exc:
        raise TtlImportError("unreadable turtle") from exc

    prj_ns = prefixes.get("prj")
    if not prj_ns:
        raise TtlImportError("project guid missing or invalid")
    match = GUID_IN_NS.search(prj_ns)
    if match is None:
        raise TtlImportError("project guid missing or invalid")
    try:
        project_guid = UUID(match.group(1))
    except ValueError as exc:
        raise TtlImportError("project guid missing or invalid") from exc

    individuals = _index_individuals(graph, prj_ns)
    installation_subject, installation_ets_id = _installation_subject(
        graph, prefixes, individuals
    )
    return ParsedTtl(
        project_guid=project_guid,
        prj_ns=prj_ns,
        graph=graph,
        prefixes=prefixes,
        individuals=individuals,
        installation_ets_id=installation_ets_id,
        installation_subject=installation_subject,
    )


def ingest_ttl(
    session: Session, path: Path, *, import_clock: datetime
) -> UpsertResult:
    """Parse ETS semantic export and upsert. Reuse ``UpsertResult``."""
    parsed = parse_ttl(path)
    try:
        return _ingest_parsed(session, parsed, import_clock=import_clock)
    except IntegrityError as exc:
        raise TtlImportError("installation violates a database constraint") from exc


def _ingest_parsed(
    session: Session, parsed: ParsedTtl, *, import_clock: datetime
) -> UpsertResult:
    import_clock = _aware_utc(import_clock)
    result = _upsert_installation(session, parsed, import_clock=import_clock)
    fallback = result.version.last_modified
    locations_by_ets = _upsert_locations(session, result.installation, parsed, fallback)
    functions_by_ets = _upsert_functions(
        session, result.installation, parsed, locations_by_ets, fallback
    )
    _upsert_devices(session, result.installation, parsed, locations_by_ets, fallback)
    datapoints_by_ets = _upsert_datapoints(
        session, result.installation, parsed, fallback
    )
    _upsert_function_datapoints(
        session,
        result.installation,
        parsed,
        functions_by_ets,
        datapoints_by_ets,
        fallback,
    )
    return result


def _upsert_installation(
    session: Session, parsed: ParsedTtl, *, import_clock: datetime
) -> UpsertResult:
    graph = parsed.graph
    prefixes = parsed.prefixes
    subject = parsed.installation_subject
    title = _node_str(graph.value(subject, _uri(prefixes, "dct", "title"))) or (
        parsed.installation_ets_id
    )
    comment = _node_str(graph.value(subject, _uri(prefixes, "core", "comment")))
    completion_status = _completion_status(
        _node_str(graph.value(subject, _uri(prefixes, "core", "state")))
    )
    last_modified = _datetime_from_node(
        graph.value(subject, _uri(prefixes, "core", "lastModified"))
    )
    if last_modified is None:
        last_modified = import_clock
    mac_version = _node_str(graph.value(subject, _uri(prefixes, "knx", "macVersion")))

    installation = session.scalars(
        select(Installation)
        .where(Installation.project_guid == parsed.project_guid)
        .options(selectinload(Installation.versions))
    ).first()

    version_fields = {
        "title": title,
        "comment": comment,
        "contract_number": None,
        "project_installation_number": None,
        "completion_status": completion_status,
        "project_type": None,
        "master_data_version": None,
        "schema_version": None,
        "created_by": None,
        "tool_version": mac_version,
        "ip_routing_backbone_key": None,
        "bcu_key": None,
        "group_address_style": None,
        "last_modified": last_modified,
    }

    if installation is None:
        installation = Installation(
            id=uuid4(),
            ets_id=parsed.installation_ets_id,
            project_guid=parsed.project_guid,
            last_import=import_clock,
        )
        session.add(installation)
        session.flush()
        version = InstallationVersion(
            installation_id=installation.id,
            **version_fields,
        )
        session.add(version)
        session.flush()
        return UpsertResult(
            installation=installation,
            version=version,
            created=True,
            versioned=True,
        )

    installation.last_import = import_clock
    session.flush()

    current = max(installation.versions, key=lambda item: item.last_modified)
    if current.tool_version:
        version_fields["tool_version"] = current.tool_version
    _preserve(version_fields, current, INSTALLATION_PRESERVE_FIELDS)

    existing_at_modified = next(
        (item for item in installation.versions if item.last_modified == last_modified),
        None,
    )
    if existing_at_modified is not None:
        return UpsertResult(
            installation=installation,
            version=current,
            created=False,
            versioned=False,
        )

    incoming = tuple(
        _cmp_value(version_fields[name]) for name in INSTALLATION_SEMANTIC_FIELDS
    )
    existing = tuple(
        _cmp_value(getattr(current, name)) for name in INSTALLATION_SEMANTIC_FIELDS
    )
    if incoming == existing:
        return UpsertResult(
            installation=installation,
            version=current,
            created=False,
            versioned=False,
        )

    version = InstallationVersion(
        installation_id=installation.id,
        **version_fields,
    )
    session.add(version)
    session.flush()
    return UpsertResult(
        installation=installation,
        version=version,
        created=False,
        versioned=True,
    )


def _upsert_locations(
    session: Session,
    installation: Installation,
    parsed: ParsedTtl,
    fallback: datetime,
) -> dict[str, Location]:
    graph = parsed.graph
    prefixes = parsed.prefixes
    rows: list[tuple[str, URIRef, list[str]]] = []
    for ets_id, subject in parsed.individuals.items():
        if not LOCATION_ETS.fullmatch(ets_id):
            continue
        at_type = _rdf_types(graph, subject, prefixes)
        if _is_site(ets_id, at_type):
            continue
        if not any(curie.startswith("loc:") for curie in at_type):
            continue
        rows.append((ets_id, subject, at_type))

    parent_of = _invert_location_parents(parsed)
    by_ets = _by_ets(session, Location, installation.id)
    new_identities: list[Location] = []
    for ets_id, _subject, _at_type in rows:
        if ets_id in by_ets:
            continue
        location = Location(
            id=uuid4(),
            installation_id=installation.id,
            ets_id=ets_id,
        )
        session.add(location)
        by_ets[ets_id] = location
        new_identities.append(location)
    if new_identities:
        session.flush()

    for ets_id, subject, at_type in rows:
        location = by_ets[ets_id]
        parent_ets = parent_of.get(ets_id)
        parent_location_id = None
        if parent_ets and parent_ets != ets_id:
            parent = by_ets.get(parent_ets)
            if parent is not None:
                parent_location_id = parent.id
        title = _node_str(graph.value(subject, _uri(prefixes, "dct", "title"))) or ets_id
        usage_node = graph.value(subject, _uri(prefixes, "tag", "hasLocationUsage"))
        current = (
            max(location.versions, key=lambda item: item.last_modified)
            if location.versions
            else None
        )
        fields = {
            "title": title,
            "description": _node_str(
                graph.value(subject, _uri(prefixes, "dct", "description"))
            ),
            "comment": _node_str(
                graph.value(subject, _uri(prefixes, "core", "comment"))
            ),
            "number": _node_str(graph.value(subject, _uri(prefixes, "core", "number"))),
            "location_type": _location_type(at_type),
            "usage": _curie_of(usage_node, prefixes),
            "completion_status": _completion_status(
                _node_str(graph.value(subject, _uri(prefixes, "core", "state")))
            ),
            "at_type": _norm_str_list(at_type),
            "parent_location_id": parent_location_id,
            "default_line_id": None,
            "last_modified": _last_modified(
                graph.value(subject, _uri(prefixes, "core", "lastModified")),
                fallback,
            ),
        }
        _upsert_version(
            session,
            versions=location.versions,
            version_cls=LocationVersion,
            fk={"location_id": location.id},
            semantic_fields=LOCATION_SEMANTIC_FIELDS,
            fields=fields,
            preserve_from=current,
            preserve_fields=LOCATION_PRESERVE_FIELDS,
        )
    session.flush()
    return by_ets


def _upsert_functions(
    session: Session,
    installation: Installation,
    parsed: ParsedTtl,
    locations_by_ets: dict[str, Location],
    fallback: datetime,
) -> dict[str, Function]:
    graph = parsed.graph
    prefixes = parsed.prefixes
    app_fn = _uri(prefixes, "core", "ApplicationFunction")
    host_of = _invert_simple(
        parsed, _uri(prefixes, "loc", "hasApplicationFunction")
    )
    rows: list[tuple[str, URIRef]] = []
    for ets_id, subject in parsed.individuals.items():
        if not FUNCTION_ETS.fullmatch(ets_id):
            continue
        if app_fn not in graph.objects(subject, RDF.type):
            continue
        rows.append((ets_id, subject))

    by_ets = _functions_by_ets(session, installation.id)
    new_identities: list[Function] = []
    for ets_id, _subject in rows:
        if ets_id in by_ets:
            continue
        function = Function(
            id=uuid4(),
            installation_id=installation.id,
            ets_id=ets_id,
        )
        session.add(function)
        by_ets[ets_id] = function
        new_identities.append(function)
    if new_identities:
        session.flush()

    for ets_id, subject in rows:
        function = by_ets[ets_id]
        current = (
            max(function.versions, key=lambda item: item.last_modified)
            if function.versions
            else None
        )
        function_type = "FT-0"
        if current is not None and current.function_type_ets_id:
            function_type = current.function_type_ets_id
        location_id = None
        host_ets = host_of.get(ets_id)
        if host_ets:
            host = locations_by_ets.get(host_ets)
            if host is not None:
                location_id = host.id
        title = _node_str(graph.value(subject, _uri(prefixes, "dct", "title"))) or ets_id
        at_type = _rdf_types(graph, subject, prefixes)
        fields = {
            "title": title,
            "description": _node_str(
                graph.value(subject, _uri(prefixes, "dct", "description"))
            ),
            "comment": _node_str(
                graph.value(subject, _uri(prefixes, "core", "comment"))
            ),
            "function_type_ets_id": function_type,
            "at_type": _norm_str_list(at_type),
            "location_id": location_id,
            "completion_status": _completion_status(
                _node_str(graph.value(subject, _uri(prefixes, "core", "state")))
            ),
            "last_modified": _last_modified(
                graph.value(subject, _uri(prefixes, "core", "lastModified")),
                fallback,
            ),
        }
        _upsert_version(
            session,
            versions=function.versions,
            version_cls=FunctionVersion,
            fk={"function_id": function.id},
            semantic_fields=FUNCTION_SEMANTIC_FIELDS,
            fields=fields,
            preserve_from=None,
            preserve_fields=(),
        )
    session.flush()
    return by_ets


def _upsert_devices(
    session: Session,
    installation: Installation,
    parsed: ParsedTtl,
    locations_by_ets: dict[str, Location],
    fallback: datetime,
) -> None:
    graph = parsed.graph
    prefixes = parsed.prefixes
    device_type = _uri(prefixes, "core", "Device")
    location_of = _invert_simple(
        parsed, _uri(prefixes, "loc", "containsEquipment")
    )
    rows: list[tuple[str, URIRef]] = []
    for ets_id, subject in parsed.individuals.items():
        if not DEVICE_ETS.fullmatch(ets_id):
            continue
        if device_type not in graph.objects(subject, RDF.type):
            continue
        rows.append((ets_id, subject))

    by_ets = _devices_by_ets(session, installation.id)
    new_identities: list[Device] = []
    for ets_id, _subject in rows:
        if ets_id in by_ets:
            continue
        device = Device(
            id=uuid4(),
            installation_id=installation.id,
            ets_id=ets_id,
        )
        session.add(device)
        by_ets[ets_id] = device
        new_identities.append(device)
    if new_identities:
        session.flush()

    for ets_id, subject in rows:
        device = by_ets[ets_id]
        current = (
            max(device.versions, key=lambda item: item.last_modified)
            if device.versions
            else None
        )
        product = graph.value(subject, _uri(prefixes, "core", "hasProduct"))
        hosts = graph.value(subject, _uri(prefixes, "core", "hosts"))
        location_id = None
        host_ets = location_of.get(ets_id)
        if host_ets:
            host = locations_by_ets.get(host_ets)
            if host is not None:
                location_id = host.id
        title = _node_str(graph.value(subject, _uri(prefixes, "dct", "title"))) or ets_id
        fields = {
            "title": title,
            "description": _node_str(
                graph.value(subject, _uri(prefixes, "dct", "description"))
            ),
            "comment": _node_str(
                graph.value(subject, _uri(prefixes, "core", "comment"))
            ),
            "order_number": _node_str(
                graph.value(product, _uri(prefixes, "core", "orderNumber"))
            )
            if isinstance(product, URIRef)
            else None,
            "manufacturer": _node_str(
                graph.value(product, _uri(prefixes, "core", "manufacturer"))
            )
            if isinstance(product, URIRef)
            else None,
            "last_downloaded": _last_downloaded(
                graph.value(subject, _uri(prefixes, "core", "lastDownloaded"))
            ),
            "serial_number": _serial_number(
                _node_str(graph.value(subject, _uri(prefixes, "core", "serialNumber")))
            ),
            "individual_address": _individual_address(
                _node_str(
                    graph.value(subject, _uri(prefixes, "knx", "individualAddress"))
                )
            ),
            "firmware_version": None,
            "hardware_version": None,
            "completion_status": _completion_status(
                _node_str(graph.value(subject, _uri(prefixes, "core", "state")))
            ),
            "communication_part_loaded": False,
            "individual_address_loaded": False,
            "application_program_loaded": False,
            "parameters_loaded": False,
            "medium_config_loaded": False,
            "product_ref": _fragment(product, parsed.prj_ns),
            "application_program_ref": _fragment(hosts, parsed.prj_ns),
            "bus_current": _node_int(
                graph.value(subject, _uri(prefixes, "mac", "busCurrent"))
            ),
            "installation_hints": _node_str(
                graph.value(subject, _uri(prefixes, "knx", "installationHints"))
            ),
            "at_type": _norm_str_list(_rdf_types(graph, subject, prefixes)),
            "location_id": location_id,
            "segment_id": None,
            "assigned_trade": _node_str(
                graph.value(subject, _uri(prefixes, "mac", "assignedTrade"))
            ),
            "operates_for_trade": _norm_str_list(
                [
                    curie
                    for obj in graph.objects(
                        subject, _uri(prefixes, "tag", "operatesForTrade")
                    )
                    if (curie := _curie_of(obj, prefixes))
                ]
            ),
            "last_modified": _last_modified(
                graph.value(subject, _uri(prefixes, "core", "lastModified")),
                fallback,
            ),
        }
        _upsert_version(
            session,
            versions=device.versions,
            version_cls=DeviceVersion,
            fk={"device_id": device.id},
            semantic_fields=TTL_DEVICE_SEMANTIC_FIELDS,
            fields=fields,
            preserve_from=current,
            preserve_fields=DEVICE_PRESERVE_FIELDS,
        )
    session.flush()


def _upsert_datapoints(
    session: Session,
    installation: Installation,
    parsed: ParsedTtl,
    fallback: datetime,
) -> dict[str, Datapoint]:
    graph = parsed.graph
    prefixes = parsed.prefixes
    fp_type = _uri(prefixes, "knx", "FunctionPoint")
    rows: list[tuple[str, URIRef]] = []
    for ets_id, subject in parsed.individuals.items():
        if not DATAPOINT_ETS.fullmatch(ets_id):
            continue
        if fp_type not in graph.objects(subject, RDF.type):
            continue
        rows.append((ets_id, subject))

    by_ets = _datapoints_by_ets(session, installation.id)
    new_identities: list[Datapoint] = []
    for ets_id, _subject in rows:
        if ets_id in by_ets:
            continue
        datapoint = Datapoint(
            id=uuid4(),
            installation_id=installation.id,
            ets_id=ets_id,
        )
        session.add(datapoint)
        by_ets[ets_id] = datapoint
        new_identities.append(datapoint)
    if new_identities:
        session.flush()

    for ets_id, subject in rows:
        datapoint = by_ets[ets_id]
        current = (
            max(datapoint.versions, key=lambda item: item.last_modified)
            if datapoint.versions
            else None
        )
        at_type = _rdf_types(graph, subject, prefixes)
        for obj in graph.objects(subject, _uri(prefixes, "knx", "datapointType")):
            curie = _curie_of(obj, prefixes)
            if curie and curie not in at_type:
                at_type.append(curie)
        group_address = _node_int(
            graph.value(subject, _uri(prefixes, "knx", "groupAddress"))
        )
        if group_address is not None and not 0 <= group_address <= 65535:
            group_address = None
        name = _node_str(graph.value(subject, _uri(prefixes, "dct", "title"))) or ets_id
        fields = {
            "name": name,
            "description": _node_str(
                graph.value(subject, _uri(prefixes, "dct", "description"))
            ),
            "comment": _node_str(
                graph.value(subject, _uri(prefixes, "core", "comment"))
            ),
            "group_address": group_address,
            "datapoint_subtype_ets_id": None,
            "at_type": _norm_str_list(at_type),
            "readable": _node_bool(
                graph.value(subject, _uri(prefixes, "core", "readable"))
            ),
            "writable": _node_bool(
                graph.value(subject, _uri(prefixes, "core", "writable"))
            ),
            "security": _node_str(
                graph.value(subject, _uri(prefixes, "knx", "securityMode"))
            ),
            "group_range_id": None,
            "purpose": None,
            "unfiltered": None,
            "central": None,
            "completion_status": _completion_status(
                _node_str(graph.value(subject, _uri(prefixes, "core", "state")))
            ),
            "global_": None,
            "key": None,
            "last_modified": _last_modified(
                graph.value(subject, _uri(prefixes, "core", "lastModified")),
                fallback,
            ),
        }
        _upsert_version(
            session,
            versions=datapoint.versions,
            version_cls=DatapointVersion,
            fk={"datapoint_id": datapoint.id},
            semantic_fields=DATAPOINT_SEMANTIC_FIELDS,
            fields=fields,
            preserve_from=current,
            preserve_fields=DATAPOINT_PRESERVE_FIELDS,
        )
    session.flush()
    return by_ets


def _upsert_function_datapoints(
    session: Session,
    installation: Installation,
    parsed: ParsedTtl,
    functions_by_ets: dict[str, Function],
    datapoints_by_ets: dict[str, Datapoint],
    fallback: datetime,
) -> None:
    graph = parsed.graph
    prefixes = parsed.prefixes
    has_fp = _uri(prefixes, "knx", "hasFunctionPoint")
    existing_edges = _function_datapoints_by_pair(session, installation.id)
    for ets_id, function in functions_by_ets.items():
        subject = parsed.individuals.get(ets_id)
        if subject is None:
            continue
        last_modified = _last_modified(
            graph.value(subject, _uri(prefixes, "core", "lastModified")),
            fallback,
        )
        for obj in graph.objects(subject, has_fp):
            ga_ets = _fragment(obj, parsed.prj_ns)
            if not ga_ets:
                continue
            datapoint = datapoints_by_ets.get(ga_ets)
            if datapoint is None:
                continue
            fields = {
                "ets_id": None,
                "role": None,
                "linked": True,
                "last_modified": last_modified,
            }
            pair = (function.id, datapoint.id)
            versions = existing_edges.setdefault(pair, [])
            _upsert_version(
                session,
                versions=versions,
                version_cls=FunctionDatapoint,
                fk={"function_id": function.id, "datapoint_id": datapoint.id},
                semantic_fields=FUNCTION_DATAPOINT_SEMANTIC_FIELDS,
                fields=fields,
                preserve_from=None,
                preserve_fields=(),
            )
    session.flush()


def _upsert_version(
    session: Session,
    *,
    versions: list[object],
    version_cls: type,
    fk: dict[str, UUID],
    semantic_fields: tuple[str, ...],
    fields: dict[str, object],
    preserve_from: object | None,
    preserve_fields: tuple[str, ...],
) -> None:
    if preserve_from is not None:
        _preserve(fields, preserve_from, preserve_fields)
    last_modified = fields["last_modified"]
    existing_at_modified = next(
        (item for item in versions if item.last_modified == last_modified),
        None,
    )
    if existing_at_modified is not None:
        return
    if versions:
        current = max(versions, key=lambda item: item.last_modified)
        incoming = tuple(_cmp_value(fields[name]) for name in semantic_fields)
        existing = tuple(
            _cmp_value(getattr(current, name)) for name in semantic_fields
        )
        if incoming == existing:
            return
    version = version_cls(**fk, **fields)
    session.add(version)
    versions.append(version)


def _instance_turtle(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines(keepends=True)
    prefixes = dict(KNOWN_PREFIXES)
    prefix_lines: list[str] = []
    start: int | None = None
    end: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        match = PREFIX_LINE.match(stripped)
        if match:
            prefixes[match.group(1)] = match.group(2)
            prefix_lines.append(line if line.endswith(("\n", "\r")) else f"{line}\n")
            continue
        if start is None:
            if line.startswith("prj:"):
                start = index
            continue
        col0 = COL0_CURIE.match(line)
        if col0 is not None and col0.group(1) != "prj":
            end = index
            break
    if start is None:
        raise TtlImportError("project guid missing or invalid")
    instance = lines[start:end]
    chunk = "".join(prefix_lines) + "\n" + "".join(instance)
    if not chunk.endswith("\n"):
        chunk += "\n"
    return prefixes, chunk


def _index_individuals(graph: Graph, prj_ns: str) -> dict[str, URIRef]:
    individuals: dict[str, URIRef] = {}
    for subject in graph.subjects():
        if not isinstance(subject, URIRef):
            continue
        iri = str(subject)
        if not iri.startswith(prj_ns):
            continue
        ets_id = iri[len(prj_ns) :]
        if ets_id:
            individuals[ets_id] = subject
    return individuals


def _installation_subject(
    graph: Graph,
    prefixes: dict[str, str],
    individuals: dict[str, URIRef],
) -> tuple[URIRef, str]:
    install_type = _uri(prefixes, "core", "Installation")
    found: list[tuple[URIRef, str]] = []
    for ets_id, subject in individuals.items():
        if install_type in graph.objects(subject, RDF.type):
            found.append((subject, ets_id))
    if not found:
        raise TtlImportError("installation missing")
    for subject, ets_id in found:
        if ets_id.startswith("P-"):
            return subject, ets_id
    return found[0]


def _invert_location_parents(parsed: ParsedTtl) -> dict[str, str]:
    parent_of: dict[str, str] = {}
    for ets_id, subject in parsed.individuals.items():
        for local in LOC_CHILD_PREDICATES:
            predicate = URIRef(parsed.prefixes["loc"] + local)
            for obj in parsed.graph.objects(subject, predicate):
                child_ets = _fragment(obj, parsed.prj_ns)
                if not child_ets:
                    continue
                previous = parent_of.get(child_ets)
                if previous is None or previous == "Site":
                    parent_of[child_ets] = ets_id
    return parent_of


def _invert_simple(parsed: ParsedTtl, predicate: URIRef) -> dict[str, str]:
    host_of: dict[str, str] = {}
    for ets_id, subject in parsed.individuals.items():
        for obj in parsed.graph.objects(subject, predicate):
            child_ets = _fragment(obj, parsed.prj_ns)
            if child_ets and child_ets not in host_of:
                host_of[child_ets] = ets_id
    return host_of


def _rdf_types(
    graph: Graph, subject: URIRef, prefixes: dict[str, str]
) -> list[str]:
    curies: list[str] = []
    for obj in graph.objects(subject, RDF.type):
        if str(obj) == NAMED_INDIVIDUAL:
            continue
        curie = _curie_of(obj, prefixes)
        if curie and curie not in curies:
            curies.append(curie)
    return curies


def _location_type(at_type: list[str]) -> str | None:
    for curie in at_type:
        if not curie.startswith("loc:"):
            continue
        mapped = LOC_TYPE_TO_XSD.get(curie[4:])
        if mapped is not None and mapped in LOCATION_TYPE_VALUES:
            return mapped
    return None


def _is_site(ets_id: str, at_type: list[str]) -> bool:
    return ets_id == "Site" or "loc:Site" in at_type


def _by_ets(
    session: Session, model: type[Location], installation_id: UUID
) -> dict[str, Location]:
    rows = session.scalars(
        select(model)
        .where(model.installation_id == installation_id)
        .options(selectinload(model.versions))
    ).all()
    return {row.ets_id: row for row in rows}


def _functions_by_ets(session: Session, installation_id: UUID) -> dict[str, Function]:
    rows = session.scalars(
        select(Function)
        .where(Function.installation_id == installation_id)
        .options(selectinload(Function.versions))
    ).all()
    return {row.ets_id: row for row in rows}


def _devices_by_ets(session: Session, installation_id: UUID) -> dict[str, Device]:
    rows = session.scalars(
        select(Device)
        .where(Device.installation_id == installation_id)
        .options(selectinload(Device.versions))
    ).all()
    return {row.ets_id: row for row in rows}


def _datapoints_by_ets(session: Session, installation_id: UUID) -> dict[str, Datapoint]:
    rows = session.scalars(
        select(Datapoint)
        .where(Datapoint.installation_id == installation_id)
        .options(selectinload(Datapoint.versions))
    ).all()
    return {row.ets_id: row for row in rows}


def _function_datapoints_by_pair(
    session: Session, installation_id: UUID
) -> dict[tuple[UUID, UUID], list[FunctionDatapoint]]:
    rows = session.scalars(
        select(FunctionDatapoint)
        .join(Function, Function.id == FunctionDatapoint.function_id)
        .where(Function.installation_id == installation_id)
    ).all()
    grouped: dict[tuple[UUID, UUID], list[FunctionDatapoint]] = {}
    for row in rows:
        grouped.setdefault((row.function_id, row.datapoint_id), []).append(row)
    return grouped


def _uri(prefixes: dict[str, str], prefix: str, local: str) -> URIRef:
    return URIRef(prefixes[prefix] + local)


def _curie_of(node: Node | None, prefixes: dict[str, str]) -> str | None:
    if not isinstance(node, URIRef):
        return None
    iri = str(node)
    for prefix, namespace in prefixes.items():
        if iri.startswith(namespace):
            return f"{prefix}:{iri[len(namespace):]}"
    return None


def _fragment(node: Node | None, prj_ns: str) -> str | None:
    if not isinstance(node, URIRef):
        return None
    iri = str(node)
    if iri.startswith(prj_ns):
        return iri[len(prj_ns) :] or None
    if "#" in iri:
        return iri.rsplit("#", 1)[-1] or None
    return None


def _node_str(node: Node | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, Literal):
        text = str(node)
        return text if text != "" else None
    return None


def _node_bool(node: Node | None) -> bool | None:
    if node is None:
        return None
    if isinstance(node, Literal):
        value = node.value
        if isinstance(value, bool):
            return value
        if node.datatype == XSD.boolean and isinstance(value, bool):
            return value
        text = str(node).strip()
        if text in {"True", "true", "1"}:
            return True
        if text in {"False", "false", "0"}:
            return False
    return None


def _node_int(node: Node | None) -> int | None:
    if node is None:
        return None
    if isinstance(node, Literal):
        value = node.value
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        text = str(node).strip()
        if text.isdigit():
            return int(text)
    return None


def _datetime_from_node(node: Node | None) -> datetime | None:
    if node is None:
        return None
    if isinstance(node, Literal) and isinstance(node.value, datetime):
        parsed = node.value
        if parsed.year <= 1:
            return None
        return _aware_utc(parsed)
    text = _node_str(node)
    if text is None:
        return None
    try:
        parsed = parse_ets_datetime(text)
    except (TypeError, ValueError):
        return None
    if parsed is None:
        return None
    return _aware_utc(parsed)


def _last_modified(node: Node | None, fallback: datetime) -> datetime:
    parsed = _datetime_from_node(node)
    if parsed is None:
        parsed = fallback
    return _aware_utc(parsed)


def _last_downloaded(node: Node | None) -> datetime | None:
    text = _node_str(node)
    if text is None or text.startswith("0001-01-01"):
        return None
    try:
        parsed = parse_ets_datetime(text)
    except (TypeError, ValueError):
        return None
    if parsed is None or parsed.year <= 1:
        return None
    return _aware_utc(parsed)


def _serial_number(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = raw[1:] if raw.startswith("$") else raw
    if not text:
        return None
    if len(text) == 12:
        try:
            data = bytes.fromhex(text)
        except ValueError:
            return text
        if len(data) == 6:
            return base64.b64encode(data).decode("ascii")
    return text


def _individual_address(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = raw.strip()
    if text.startswith(("0x", "0X")):
        text = text[2:]
    try:
        number = int(text, 16)
    except ValueError:
        return None
    number &= 0xFFFF
    area = (number >> 12) & 0xF
    line = (number >> 8) & 0xF
    device = number & 0xFF
    return f"{area}.{line}.{device}"


def _completion_status(raw: str | None) -> str | None:
    if raw is None:
        return None
    if raw not in COMPLETION_STATUS_VALUES:
        raise TtlImportError(f"unsupported completion status {raw!r}")
    return raw


def _preserve(
    fields: dict[str, object], current: object, names: tuple[str, ...]
) -> None:
    for name in names:
        incoming = fields.get(name)
        if incoming is None or (
            name in DEVICE_LOADED_FIELDS and incoming is False
        ):
            current_value = getattr(current, name)
            if current_value is not None:
                fields[name] = current_value


def _norm_str_list(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    return sorted(set(values))


def _cmp_value(value: object) -> object:
    if isinstance(value, list):
        return tuple(value)
    return value


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
