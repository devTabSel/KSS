"""Serialize an installation snapshot as ETS-style instance Turtle."""

from __future__ import annotations

import base64
from datetime import datetime

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from kss.services.snapshot import (
    DeviceSnap,
    InstallationSnapshot,
    LocationSnap,
    TtlStatement,
)
from kss.services.temporal import isoformat_utc
from kss.services.ttl import KNOWN_PREFIXES, LOC_TYPE_TO_XSD

XSD_TO_LOC = {xsd: loc for loc, xsd in LOC_TYPE_TO_XSD.items()}
XSD_TO_LOC.setdefault("BuildingPart", "Space")

CHILD_PREDICATE = {
    "Building": "hasBuilding",
    "Floor": "hasFloor",
    "Room": "hasRoom",
    "BuildingPart": "hasSpace",
    "Space": "hasSpace",
}


def serialize_ttl(snap: InstallationSnapshot) -> str:
    graph = Graph()
    for prefix, namespace in KNOWN_PREFIXES.items():
        graph.bind(prefix, namespace)
    prj_ns = f"http://iot.knx.org/{snap.installation.project_guid}#"
    graph.bind("prj", prj_ns)

    _add_installation(graph, snap, prj_ns)
    locations_by_id = {item.location.id: item for item in snap.locations}
    for item in snap.locations:
        _add_location(graph, snap, item, locations_by_id, prj_ns)
    functions_by_id = {item.function.id: item for item in snap.functions}
    datapoints_by_id = {item.datapoint.id: item for item in snap.datapoints}
    for item in snap.functions:
        _add_function(graph, snap, item, locations_by_id, prj_ns)
    for edge in snap.function_datapoints:
        function = functions_by_id.get(edge.function_id)
        datapoint = datapoints_by_id.get(edge.datapoint_id)
        if function is None or datapoint is None:
            continue
        graph.add(
            (
                _prj(prj_ns, function.function.ets_id),
                _curie(KNOWN_PREFIXES, "knx:hasFunctionPoint"),
                _prj(prj_ns, datapoint.datapoint.ets_id),
            )
        )
    for item in snap.devices:
        _add_device(graph, snap, item, locations_by_id, prj_ns)
    for item in snap.datapoints:
        _add_datapoint(graph, item, prj_ns)
    for statement in snap.contributions.ttl:
        _add_statement(graph, prj_ns, statement)

    return _canonical_turtle(graph, prj_ns)


def _add_installation(graph: Graph, snap: InstallationSnapshot, prj_ns: str) -> None:
    subject = _prj(prj_ns, snap.installation.ets_id)
    _named(graph, subject)
    graph.add((subject, RDF.type, _curie(KNOWN_PREFIXES, "core:Installation")))
    _literal(graph, subject, "dct:title", snap.version.title)
    _literal(graph, subject, "core:comment", snap.version.comment)
    _literal(graph, subject, "core:state", snap.version.completion_status)
    _datetime(graph, subject, "core:lastModified", snap.version.last_modified)
    _literal(graph, subject, "knx:macVersion", snap.version.tool_version)
    _literal(graph, subject, "knx:contractNumber", snap.version.contract_number)
    _literal(
        graph,
        subject,
        "knx:projectInstallationNumber",
        snap.version.project_installation_number,
    )


def _add_location(
    graph: Graph,
    snap: InstallationSnapshot,
    item: LocationSnap,
    locations_by_id: dict,
    prj_ns: str,
) -> None:
    subject = _prj(prj_ns, item.location.ets_id)
    _named(graph, subject)
    types = list(item.version.at_type or [])
    loc_class = XSD_TO_LOC.get(item.version.location_type or "")
    if loc_class:
        curie = f"loc:{loc_class}"
        if curie not in types:
            types.append(curie)
    for curie in types:
        graph.add((subject, RDF.type, _curie(KNOWN_PREFIXES, curie)))
    _literal(graph, subject, "dct:title", item.version.title)
    _literal(graph, subject, "dct:description", item.version.description)
    _literal(graph, subject, "core:comment", item.version.comment)
    _literal(graph, subject, "core:number", item.version.number)
    _literal(graph, subject, "core:state", item.version.completion_status)
    _datetime(graph, subject, "core:lastModified", item.version.last_modified)
    if item.version.usage:
        graph.add(
            (
                subject,
                _curie(KNOWN_PREFIXES, "tag:hasLocationUsage"),
                _curie(KNOWN_PREFIXES, item.version.usage),
            )
        )
    parent_id = item.version.parent_location_id
    if parent_id is None or parent_id not in locations_by_id:
        return
    parent = locations_by_id[parent_id]
    predicate = CHILD_PREDICATE.get(item.version.location_type or "", "hasLocation")
    graph.add(
        (
            _prj(prj_ns, parent.location.ets_id),
            _curie(KNOWN_PREFIXES, f"loc:{predicate}"),
            subject,
        )
    )
    del snap


def _add_function(
    graph: Graph,
    snap: InstallationSnapshot,
    item,
    locations_by_id: dict,
    prj_ns: str,
) -> None:
    subject = _prj(prj_ns, item.function.ets_id)
    _named(graph, subject)
    types = list(item.version.at_type or ["core:ApplicationFunction"])
    if "core:ApplicationFunction" not in types:
        types.append("core:ApplicationFunction")
    for curie in types:
        graph.add((subject, RDF.type, _curie(KNOWN_PREFIXES, curie)))
    _literal(graph, subject, "dct:title", item.version.title)
    _literal(graph, subject, "dct:description", item.version.description)
    _literal(graph, subject, "core:comment", item.version.comment)
    _literal(graph, subject, "core:state", item.version.completion_status)
    _datetime(graph, subject, "core:lastModified", item.version.last_modified)
    location_id = item.version.location_id
    if location_id is not None and location_id in locations_by_id:
        host = locations_by_id[location_id]
        graph.add(
            (
                _prj(prj_ns, host.location.ets_id),
                _curie(KNOWN_PREFIXES, "loc:hasApplicationFunction"),
                subject,
            )
        )
    del snap


def _add_device(
    graph: Graph,
    snap: InstallationSnapshot,
    item: DeviceSnap,
    locations_by_id: dict,
    prj_ns: str,
) -> None:
    subject = _prj(prj_ns, item.device.ets_id)
    _named(graph, subject)
    types = list(item.version.at_type or ["core:Device"])
    if "core:Device" not in types:
        types.append("core:Device")
    for curie in types:
        graph.add((subject, RDF.type, _curie(KNOWN_PREFIXES, curie)))
    _literal(graph, subject, "dct:title", item.version.title)
    _literal(graph, subject, "dct:description", item.version.description)
    _literal(graph, subject, "core:comment", item.version.comment)
    _literal(graph, subject, "core:state", item.version.completion_status)
    _datetime(graph, subject, "core:lastModified", item.version.last_modified)
    _datetime(graph, subject, "core:lastDownloaded", item.version.last_downloaded)
    serial = _serial_ttl(item.version.serial_number)
    _literal(graph, subject, "core:serialNumber", serial)
    ia_hex = _ia_hex(item.version.individual_address)
    _literal(graph, subject, "knx:individualAddress", ia_hex)
    if item.version.bus_current is not None:
        graph.add(
            (
                subject,
                _curie(KNOWN_PREFIXES, "mac:busCurrent"),
                Literal(item.version.bus_current, datatype=XSD.integer),
            )
        )
    _literal(graph, subject, "knx:installationHints", item.version.installation_hints)
    _literal(graph, subject, "mac:assignedTrade", item.version.assigned_trade)
    for tag in item.version.operates_for_trade or []:
        graph.add(
            (
                subject,
                _curie(KNOWN_PREFIXES, "tag:operatesForTrade"),
                _curie(KNOWN_PREFIXES, tag),
            )
        )
    if item.version.order_number or item.version.manufacturer:
        product = _prj(prj_ns, f"{item.device.ets_id}-product")
        graph.add((subject, _curie(KNOWN_PREFIXES, "core:hasProduct"), product))
        _literal(graph, product, "core:orderNumber", item.version.order_number)
        _literal(graph, product, "core:manufacturer", item.version.manufacturer)
    location_id = item.version.location_id
    if location_id is not None and location_id in locations_by_id:
        host = locations_by_id[location_id]
        graph.add(
            (
                _prj(prj_ns, host.location.ets_id),
                _curie(KNOWN_PREFIXES, "loc:containsEquipment"),
                subject,
            )
        )
    del snap


def _add_datapoint(graph: Graph, item, prj_ns: str) -> None:
    subject = _prj(prj_ns, item.datapoint.ets_id)
    _named(graph, subject)
    types = list(item.version.at_type or ["knx:FunctionPoint"])
    if "knx:FunctionPoint" not in types:
        types.append("knx:FunctionPoint")
    for curie in types:
        graph.add((subject, RDF.type, _curie(KNOWN_PREFIXES, curie)))
    _literal(graph, subject, "dct:title", item.version.name)
    _literal(graph, subject, "dct:description", item.version.description)
    _literal(graph, subject, "core:comment", item.version.comment)
    _literal(graph, subject, "core:state", item.version.completion_status)
    _datetime(graph, subject, "core:lastModified", item.version.last_modified)
    if item.version.group_address is not None:
        graph.add(
            (
                subject,
                _curie(KNOWN_PREFIXES, "knx:groupAddress"),
                Literal(item.version.group_address, datatype=XSD.integer),
            )
        )
    if item.version.readable is not None:
        graph.add(
            (
                subject,
                _curie(KNOWN_PREFIXES, "core:readable"),
                Literal(item.version.readable, datatype=XSD.boolean),
            )
        )
    if item.version.writable is not None:
        graph.add(
            (
                subject,
                _curie(KNOWN_PREFIXES, "core:writable"),
                Literal(item.version.writable, datatype=XSD.boolean),
            )
        )
    _literal(graph, subject, "knx:securityMode", item.version.security)


def _add_statement(graph: Graph, prj_ns: str, statement: TtlStatement) -> None:
    subject = _prj(prj_ns, statement.subject)
    predicate = (
        RDF.type
        if statement.predicate == "rdf:type"
        else _curie(KNOWN_PREFIXES, statement.predicate)
    )
    if statement.object_kind == "prj":
        obj: URIRef | Literal = _prj(prj_ns, statement.object)
    elif statement.object_kind == "curie":
        obj = _curie(KNOWN_PREFIXES, statement.object)
    elif statement.object_kind == "datetime":
        obj = Literal(statement.object, datatype=XSD.dateTime)
    elif statement.object_kind == "bool":
        obj = Literal(statement.object.lower() in {"true", "1"}, datatype=XSD.boolean)
    elif statement.object_kind == "int":
        obj = Literal(int(statement.object), datatype=XSD.integer)
    else:
        obj = Literal(statement.object)
    graph.add((subject, predicate, obj))
    if statement.predicate != "rdf:type":
        _named(graph, subject)


def _named(graph: Graph, subject: URIRef) -> None:
    graph.add((subject, RDF.type, _curie(KNOWN_PREFIXES, "owl:NamedIndividual")))


def _prj(prj_ns: str, ets_id: str) -> URIRef:
    return URIRef(f"{prj_ns}{ets_id}")


def _curie(prefixes: dict[str, str], curie: str) -> URIRef:
    if curie.startswith(("http://", "https://")):
        return URIRef(curie)
    if ":" not in curie:
        return URIRef(curie)
    prefix, local = curie.split(":", 1)
    namespace = prefixes.get(prefix)
    if namespace is None:
        return URIRef(curie)
    return URIRef(f"{namespace}{local}")


def _literal(graph: Graph, subject: URIRef, predicate: str, value: str | None) -> None:
    if value is None or value == "":
        return
    graph.add((subject, _curie(KNOWN_PREFIXES, predicate), Literal(value)))


def _datetime(
    graph: Graph, subject: URIRef, predicate: str, value: datetime | None
) -> None:
    if value is None:
        return
    graph.add(
        (
            subject,
            _curie(KNOWN_PREFIXES, predicate),
            Literal(isoformat_utc(value), datatype=XSD.dateTime),
        )
    )


def _serial_ttl(raw: str | None) -> str | None:
    if raw is None:
        return None
    try:
        data = base64.b64decode(raw, validate=True)
    except (ValueError, TypeError):
        return raw
    if len(data) == 6:
        return f"${data.hex().upper()}"
    return raw


def _ia_hex(dotted: str | None) -> str | None:
    if not dotted:
        return None
    parts = dotted.split(".")
    if len(parts) != 3:
        return None
    try:
        area, line, device = (int(part) for part in parts)
    except ValueError:
        return None
    number = ((area & 0xF) << 12) | ((line & 0xF) << 8) | (device & 0xFF)
    return f"{number:X}"


def _canonical_turtle(graph: Graph, prj_ns: str) -> str:
    """Deterministic Turtle: sorted prefixes, subjects, predicates, objects."""
    lines = [f"@prefix {prefix}: <{namespace}> ." for prefix, namespace in KNOWN_PREFIXES.items()]
    lines.append(f"@prefix prj: <{prj_ns}> .")
    lines.append("")

    by_subject: dict[URIRef, dict[URIRef, list]] = {}
    for subject, predicate, obj in graph:
        if not isinstance(subject, URIRef):
            continue
        by_subject.setdefault(subject, {}).setdefault(predicate, []).append(obj)

    def subject_key(uri: URIRef) -> tuple[int, str]:
        iri = str(uri)
        if iri.startswith(prj_ns):
            return (0, iri[len(prj_ns) :])
        return (1, iri)

    for subject in sorted(by_subject, key=subject_key):
        preds = by_subject[subject]
        pred_order: list[URIRef] = []
        if RDF.type in preds:
            pred_order.append(RDF.type)
        pred_order.extend(
            sorted(
                (pred for pred in preds if pred != RDF.type),
                key=lambda pred: _turtle_term(pred, prj_ns),
            )
        )
        parts: list[str] = []
        last = len(pred_order) - 1
        for index, pred in enumerate(pred_order):
            objects = sorted(
                preds[pred],
                key=lambda node: _turtle_term(node, prj_ns),
            )
            obj_txt = ", ".join(_turtle_term(node, prj_ns) for node in objects)
            pred_txt = "a" if pred == RDF.type else _turtle_term(pred, prj_ns)
            punct = " ;" if index < last else " ."
            parts.append(f"{pred_txt} {obj_txt}{punct}")
        if not parts:
            continue
        block = [f"{_turtle_term(subject, prj_ns)} {parts[0]}"]
        block.extend(f"    {part}" for part in parts[1:])
        lines.append("\n".join(block))
        lines.append("")
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    return text


def _turtle_term(node: object, prj_ns: str) -> str:
    if isinstance(node, URIRef):
        return _compact_iri(str(node), prj_ns)
    if isinstance(node, Literal):
        return _turtle_literal(node, prj_ns)
    return str(node)


def _compact_iri(iri: str, prj_ns: str) -> str:
    if iri.startswith(prj_ns):
        return f"prj:{iri[len(prj_ns) :]}"
    for prefix, namespace in KNOWN_PREFIXES.items():
        if iri.startswith(namespace):
            return f"{prefix}:{iri[len(namespace) :]}"
    return f"<{iri}>"


def _turtle_literal(obj: Literal, prj_ns: str) -> str:
    datatype = obj.datatype
    value = obj.value
    if datatype == XSD.boolean or isinstance(value, bool):
        return "true" if value else "false"
    if datatype == XSD.integer and not isinstance(value, bool):
        return str(int(value))
    if isinstance(value, int) and not isinstance(value, bool) and datatype is None:
        return str(value)
    if datatype == XSD.dateTime:
        if isinstance(value, datetime):
            lex = isoformat_utc(value)
        else:
            lex = str(obj)
            if lex.endswith("+00:00"):
                lex = f"{lex[:-6]}Z"
        return f'"{lex}"^^xsd:dateTime'
    lex = _escape_turtle_lexical(str(obj))
    if obj.language:
        return f'"{lex}"@{obj.language}'
    if datatype is not None:
        return f'"{lex}"^^{_compact_iri(str(datatype), prj_ns)}'
    return f'"{lex}"'


def _escape_turtle_lexical(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
