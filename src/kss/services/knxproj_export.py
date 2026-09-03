"""Write an unencrypted .knxproj ZIP from an installation snapshot."""

from __future__ import annotations

from io import BytesIO
from uuid import UUID
from xml.etree.ElementTree import Element, SubElement, tostring
from zipfile import ZIP_DEFLATED, ZipFile

from kss.models.master import (
    MasterApplicationCommObject,
    MasterApplicationCommObjectRef,
    MasterApplicationProgram,
    MasterHardware,
    MasterHardware2Program,
    MasterProduct,
)
from kss.services.snapshot import (
    ChannelSnap,
    CommObjectSnap,
    DeviceSnap,
    FolderSnap,
    InstallationSnapshot,
    LineSnap,
    LocationSnap,
    SegmentSnap,
)
from kss.services.temporal import isoformat_utc

KNXPROJ_MEDIA_TYPE = "application/vnd.knx.knxproj+zip"
TURTLE_MEDIA_TYPE = "text/turtle"


def serialize_knxproj(snap: InstallationSnapshot, *, less_info: bool = True) -> bytes:
    project_id = _project_id(snap.installation.ets_id)
    schema = snap.version.schema_version or "23"
    xmlns = f"http://knx.org/xml/project/{schema}"
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(f"{project_id}.signature", b"")
        archive.writestr(
            "knx_master.xml",
            _knx_master_xml(xmlns, snap),
        )
        archive.writestr(
            f"{project_id}/project.xml",
            _project_xml(snap, xmlns, project_id, less_info=less_info),
        )
        archive.writestr(
            f"{project_id}/0.xml",
            _zero_xml(snap, xmlns, less_info=less_info),
        )
        for path, body in _manufacturer_xml_files(snap, xmlns):
            archive.writestr(path, body)
    return buffer.getvalue()


def xml_id(installation_ets: str, ets_id: str) -> str:
    return f"{installation_ets}_{ets_id}"


def _project_id(ets_id: str) -> str:
    if ets_id.rsplit("-", 1)[-1].isdigit():
        return ets_id.rsplit("-", 1)[0]
    return ets_id


def _knx_master_xml(xmlns: str, snap: InstallationSnapshot) -> str:
    version = snap.version.master_data_version
    root = Element("KNX", {"xmlns": xmlns})
    master = SubElement(
        root,
        "MasterData",
        {"Id": "MD-1", "Version": str(version if version is not None else 0)},
    )
    if snap.manufacturers:
        manufacturers_el = SubElement(master, "Manufacturers")
        for item in snap.manufacturers:
            attrs = {"Id": item.knx_id}
            _put(attrs, "Name", item.name)
            SubElement(manufacturers_el, "Manufacturer", attrs)
    return _dump(root)


def _project_xml(
    snap: InstallationSnapshot, xmlns: str, project_id: str, *, less_info: bool
) -> str:
    version = snap.version
    root = Element("KNX", {"xmlns": xmlns})
    if version.created_by:
        root.set("CreatedBy", version.created_by)
    if version.tool_version:
        root.set("ToolVersion", version.tool_version)
    project = SubElement(root, "Project", {"Id": project_id})
    info_attrs = {
        "Name": version.title,
        "GroupAddressStyle": version.group_address_style or "ThreeLevel",
        "Guid": str(snap.installation.project_guid),
    }
    if version.last_modified is not None:
        info_attrs["LastModified"] = isoformat_utc(version.last_modified)
    if not less_info:
        _put(info_attrs, "CompletionStatus", version.completion_status)
        _put(info_attrs, "Comment", version.comment)
        _put(info_attrs, "ProjectNumber", version.project_installation_number)
        _put(info_attrs, "ContractNumber", version.contract_number)
        _put(info_attrs, "ProjectType", version.project_type)
        if snap.installation.project_start is not None:
            info_attrs["ProjectStart"] = isoformat_utc(snap.installation.project_start)
    SubElement(project, "ProjectInformation", info_attrs)
    return _dump(root)


def _zero_xml(snap: InstallationSnapshot, xmlns: str, *, less_info: bool) -> str:
    inst_ets = snap.installation.ets_id
    root = Element("KNX", {"xmlns": xmlns})
    project = SubElement(root, "Project", {"Id": _project_id(inst_ets)})
    installations = SubElement(project, "Installations")
    inst_attrs: dict[str, str] = {"Name": ""}
    if not less_info:
        _put(inst_attrs, "BCUKey", snap.version.bcu_key)
        _put(inst_attrs, "IPRoutingBackboneKey", snap.version.ip_routing_backbone_key)
        _put(inst_attrs, "CompletionStatus", snap.version.completion_status)
    installation = SubElement(installations, "Installation", inst_attrs)
    _write_group_addresses(installation, snap, inst_ets)
    _write_topology(installation, snap, inst_ets, less_info=less_info)
    _write_locations(installation, snap, inst_ets)
    if not less_info:
        _write_trades(installation, snap, inst_ets)
    _merge_xml_fragments(installation, snap, inst_ets)
    return _dump(root)


def _manufacturer_xml_files(
    snap: InstallationSnapshot, xmlns: str
) -> list[tuple[str, str]]:
    files: list[tuple[str, str]] = []
    products_by_hardware: dict[str, list[MasterProduct]] = {}
    for product in snap.products:
        products_by_hardware.setdefault(product.hardware_knx_id, []).append(product)
    h2p_by_hardware: dict[str, list[MasterHardware2Program]] = {}
    for program in snap.hardware2programs:
        h2p_by_hardware.setdefault(program.hardware_knx_id, []).append(program)
    hardware_by_manufacturer: dict[str, list[MasterHardware]] = {}
    for hardware in snap.hardware:
        hardware_by_manufacturer.setdefault(
            hardware.manufacturer_knx_id, []
        ).append(hardware)
    for manufacturer_knx_id in sorted(hardware_by_manufacturer):
        files.append(
            (
                f"{manufacturer_knx_id}/Hardware.xml",
                _hardware_xml(
                    xmlns,
                    manufacturer_knx_id,
                    hardware_by_manufacturer[manufacturer_knx_id],
                    products_by_hardware,
                    h2p_by_hardware,
                ),
            )
        )
    cos_by_program: dict[UUID, list[MasterApplicationCommObject]] = {}
    for comm in snap.application_comm_objects:
        cos_by_program.setdefault(comm.application_program_id, []).append(comm)
    refs_by_program: dict[UUID, list[MasterApplicationCommObjectRef]] = {}
    for ref in snap.application_comm_object_refs:
        refs_by_program.setdefault(ref.application_program_id, []).append(ref)
    for program in sorted(snap.application_programs, key=lambda row: row.knx_id):
        files.append(
            (
                f"{program.manufacturer_knx_id}/{program.knx_id}.xml",
                _application_program_xml(
                    xmlns,
                    program,
                    cos_by_program.get(program.id, []),
                    refs_by_program.get(program.id, []),
                ),
            )
        )
    return files


def _hardware_xml(
    xmlns: str,
    manufacturer_knx_id: str,
    hardware_rows: list[MasterHardware],
    products_by_hardware: dict[str, list[MasterProduct]],
    h2p_by_hardware: dict[str, list[MasterHardware2Program]],
) -> str:
    root = Element("KNX", {"xmlns": xmlns})
    manufacturer_data = SubElement(root, "ManufacturerData")
    manufacturer = SubElement(
        manufacturer_data, "Manufacturer", {"RefId": manufacturer_knx_id}
    )
    hardware_parent = SubElement(manufacturer, "Hardware")
    for hardware in sorted(hardware_rows, key=lambda row: row.knx_id):
        attrs = {"Id": hardware.knx_id}
        _put(attrs, "Name", hardware.name)
        hardware_el = SubElement(hardware_parent, "Hardware", attrs)
        products = products_by_hardware.get(hardware.knx_id, [])
        if products:
            products_el = SubElement(hardware_el, "Products")
            for product in sorted(products, key=lambda row: row.knx_id):
                product_attrs = {"Id": product.knx_id}
                _put(product_attrs, "Text", product.text)
                _put(product_attrs, "OrderNumber", product.order_number)
                SubElement(products_el, "Product", product_attrs)
        h2ps = h2p_by_hardware.get(hardware.knx_id, [])
        if h2ps:
            h2p_parent = SubElement(hardware_el, "Hardware2Programs")
            for h2p in sorted(h2ps, key=lambda row: row.knx_id):
                h2p_el = SubElement(
                    h2p_parent, "Hardware2Program", {"Id": h2p.knx_id}
                )
                SubElement(
                    h2p_el,
                    "ApplicationProgramRef",
                    {"RefId": h2p.application_program_knx_id},
                )
    return _dump(root)


def _application_program_xml(
    xmlns: str,
    program: MasterApplicationProgram,
    comm_objects: list[MasterApplicationCommObject],
    refs: list[MasterApplicationCommObjectRef],
) -> str:
    root = Element("KNX", {"xmlns": xmlns})
    manufacturer_data = SubElement(root, "ManufacturerData")
    manufacturer = SubElement(
        manufacturer_data, "Manufacturer", {"RefId": program.manufacturer_knx_id}
    )
    programs_el = SubElement(manufacturer, "ApplicationPrograms")
    application = SubElement(
        programs_el, "ApplicationProgram", {"Id": program.knx_id}
    )
    static = SubElement(application, "Static")
    prefix = f"{program.knx_id}_"
    if comm_objects:
        cos_el = SubElement(static, "ComObjects")
        for comm in comm_objects:
            attrs = {"Id": f"{prefix}{comm.knx_id}"}
            _put(attrs, "Name", comm.name)
            _put(attrs, "Text", comm.text)
            if comm.number is not None:
                attrs["Number"] = str(comm.number)
            _put(attrs, "FunctionText", comm.function_text)
            _put(attrs, "ObjectSize", comm.object_size)
            _put(attrs, "DatapointType", comm.datapoint_type_ref)
            SubElement(cos_el, "ComObject", attrs)
    if refs:
        refs_el = SubElement(static, "ComObjectRefs")
        by_id = {comm.id: comm for comm in comm_objects}
        for ref in refs:
            attrs = {"Id": f"{prefix}{ref.knx_id}"}
            parent = by_id.get(ref.comm_object_id) if ref.comm_object_id else None
            if parent is not None:
                attrs["RefId"] = f"{prefix}{parent.knx_id}"
            elif "_R-" in ref.knx_id:
                attrs["RefId"] = f"{prefix}{ref.knx_id.split('_R-', 1)[0]}"
            _put(attrs, "Name", ref.name)
            _put(attrs, "Text", ref.text)
            _put(attrs, "FunctionText", ref.function_text)
            _put(attrs, "ObjectSize", ref.object_size)
            _put(attrs, "DatapointType", ref.datapoint_type_ref)
            SubElement(refs_el, "ComObjectRef", attrs)
    return _dump(root)


def _write_group_addresses(
    installation: Element, snap: InstallationSnapshot, inst_ets: str
) -> None:
    group_addresses = SubElement(installation, "GroupAddresses")
    group_ranges_el = SubElement(group_addresses, "GroupRanges")
    ranges_by_id = {item.group_range.id: item for item in snap.group_ranges}
    children: dict[UUID | None, list] = {}
    for item in snap.group_ranges:
        children.setdefault(item.version.parent_group_range_id, []).append(item)
    datapoints_by_range: dict[UUID | None, list] = {}
    for item in snap.datapoints:
        datapoints_by_range.setdefault(item.version.group_range_id, []).append(item)

    def write_range(parent: Element, item) -> None:
        attrs = {"Id": xml_id(inst_ets, item.group_range.ets_id)}
        _put(attrs, "Name", item.version.name)
        if item.version.range_start is not None:
            attrs["RangeStart"] = str(item.version.range_start)
        if item.version.range_end is not None:
            attrs["RangeEnd"] = str(item.version.range_end)
        _put(attrs, "Comment", item.version.comment)
        _put(attrs, "Description", item.version.description)
        _put(attrs, "CompletionStatus", item.version.completion_status)
        element = SubElement(parent, "GroupRange", attrs)
        for child in children.get(item.group_range.id, []):
            write_range(element, child)
        for datapoint in datapoints_by_range.get(item.group_range.id, []):
            _write_group_address(element, datapoint, inst_ets)

    for item in children.get(None, []):
        write_range(group_ranges_el, item)
    for datapoint in datapoints_by_range.get(None, []):
        _write_group_address(group_ranges_el, datapoint, inst_ets)


def _write_group_address(parent: Element, item, inst_ets: str) -> None:
    attrs = {"Id": xml_id(inst_ets, item.datapoint.ets_id)}
    if item.version.group_address is not None:
        attrs["Address"] = str(item.version.group_address)
    _put(attrs, "Name", item.version.name)
    _put(attrs, "Description", item.version.description)
    _put(attrs, "Comment", item.version.comment)
    _put(attrs, "DatapointType", item.version.datapoint_subtype_ets_id)
    _put(attrs, "CompletionStatus", item.version.completion_status)
    _put(attrs, "Security", item.version.security)
    SubElement(parent, "GroupAddress", attrs)


def _write_topology(
    installation: Element,
    snap: InstallationSnapshot,
    inst_ets: str,
    *,
    less_info: bool,
) -> None:
    topology = SubElement(installation, "Topology")
    lines_by_area: dict[UUID, list[LineSnap]] = {}
    for item in snap.lines:
        lines_by_area.setdefault(item.version.area_id, []).append(item)
    segments_by_line: dict[UUID, list[SegmentSnap]] = {}
    for item in snap.segments:
        segments_by_line.setdefault(item.version.line_id, []).append(item)
    devices_by_segment: dict[UUID, list[DeviceSnap]] = {}
    devices_by_line: dict[UUID, list[DeviceSnap]] = {}
    segments_by_id = {item.segment.id: item for item in snap.segments}
    lines_by_id = {item.line.id: item for item in snap.lines}
    for item in snap.devices:
        if less_info and not item.version.individual_address:
            continue
        segment_id = item.version.segment_id
        if segment_id is not None and segment_id in segments_by_id:
            devices_by_segment.setdefault(segment_id, []).append(item)
            continue
        line_id = _line_for_device(item, snap, lines_by_id)
        if line_id is not None:
            devices_by_line.setdefault(line_id, []).append(item)

    for area in snap.areas:
        area_attrs = {
            "Id": xml_id(inst_ets, area.area.ets_id),
            "Address": str(area.version.address),
        }
        _put(area_attrs, "Name", area.version.name)
        _put(area_attrs, "Description", area.version.description)
        _put(area_attrs, "CompletionStatus", area.version.completion_status)
        area_el = SubElement(topology, "Area", area_attrs)
        for line in lines_by_area.get(area.area.id, []):
            line_attrs = {
                "Id": xml_id(inst_ets, line.line.ets_id),
                "Address": str(line.version.address),
            }
            _put(line_attrs, "Name", line.version.name)
            _put(line_attrs, "Description", line.version.description)
            _put(line_attrs, "CompletionStatus", line.version.completion_status)
            _put(line_attrs, "MediumTypeRefId", line.version.medium_type_ets_id)
            line_el = SubElement(area_el, "Line", line_attrs)
            for segment in segments_by_line.get(line.line.id, []):
                seg_attrs = {"Id": xml_id(inst_ets, segment.segment.ets_id)}
                _put(seg_attrs, "Name", segment.version.name)
                _put(seg_attrs, "Number", segment.version.number)
                _put(seg_attrs, "Description", segment.version.description)
                _put(seg_attrs, "CompletionStatus", segment.version.completion_status)
                _put(
                    seg_attrs,
                    "MediumTypeRefId",
                    segment.version.medium_type_ets_id
                    or line.version.medium_type_ets_id,
                )
                segment_el = SubElement(line_el, "Segment", seg_attrs)
                for device in devices_by_segment.get(segment.segment.id, []):
                    _write_device(segment_el, snap, device, inst_ets, less_info=less_info)
            for device in devices_by_line.get(line.line.id, []):
                _write_device(line_el, snap, device, inst_ets, less_info=less_info)


def _line_for_device(
    item: DeviceSnap,
    snap: InstallationSnapshot,
    lines_by_id: dict[UUID, LineSnap],
) -> UUID | None:
    ia = item.version.individual_address
    if ia:
        parts = ia.split(".")
        if len(parts) == 3:
            try:
                area_addr, line_addr, _device = (int(part) for part in parts)
            except ValueError:
                area_addr = line_addr = None
            else:
                areas = {row.area.id: row for row in snap.areas}
                for line in lines_by_id.values():
                    area = areas.get(line.version.area_id)
                    if (
                        area is not None
                        and area.version.address == area_addr
                        and line.version.address == line_addr
                    ):
                        return line.line.id
    if snap.lines:
        return snap.lines[0].line.id
    return None


def _write_device(
    parent: Element,
    snap: InstallationSnapshot,
    item: DeviceSnap,
    inst_ets: str,
    *,
    less_info: bool,
) -> None:
    attrs = {"Id": xml_id(inst_ets, item.device.ets_id)}
    address = _device_address(item.version.individual_address)
    if address is not None:
        attrs["Address"] = str(address)
    _put(attrs, "Name", item.version.title)
    _put(attrs, "Description", item.version.description)
    _put(attrs, "Comment", item.version.comment)
    _put(attrs, "ProductRefId", item.version.product_ref)
    _put(attrs, "Hardware2ProgramRefId", item.version.hardware_program_ref)
    _put(attrs, "CompletionStatus", item.version.completion_status)
    _put(attrs, "SerialNumber", item.version.serial_number)
    if item.version.last_modified is not None:
        attrs["LastModified"] = isoformat_utc(item.version.last_modified)
    if item.version.last_downloaded is not None:
        attrs["LastDownload"] = isoformat_utc(item.version.last_downloaded)
    if not less_info:
        attrs["CommunicationPartLoaded"] = _xml_bool(
            item.version.communication_part_loaded
        )
        attrs["IndividualAddressLoaded"] = _xml_bool(
            item.version.individual_address_loaded
        )
        attrs["ApplicationProgramLoaded"] = _xml_bool(
            item.version.application_program_loaded
        )
        attrs["ParametersLoaded"] = _xml_bool(item.version.parameters_loaded)
        attrs["MediumConfigLoaded"] = _xml_bool(item.version.medium_config_loaded)
        _put(attrs, "InstallationHints", item.version.installation_hints)
        if item.version.bus_current is not None:
            attrs["BusCurrent"] = str(item.version.bus_current)
        _put(attrs, "FirmwareVersion", item.version.firmware_version)
        _put(attrs, "HardwareVersion", item.version.hardware_version)
    device_el = SubElement(parent, "DeviceInstance", attrs)
    cos = [row for row in snap.comm_objects if row.comm_object.device_id == item.device.id]
    if cos:
        refs = SubElement(device_el, "ComObjectInstanceRefs")
        links_by_co = _links_by_comm_object(snap)
        channels_by_id = {row.channel.id: row for row in snap.channels}
        for comm in cos:
            _write_comm_object(refs, comm, channels_by_id, links_by_co, inst_ets)
    if not less_info:
        _write_channel_instances(device_el, snap, item.device.id, inst_ets)
        _write_group_object_tree(device_el, snap, item.device.id)


def _write_comm_object(
    parent: Element,
    item: CommObjectSnap,
    channels_by_id: dict[UUID, ChannelSnap],
    links_by_co: dict[UUID, list[str]],
    inst_ets: str,
) -> None:
    del inst_ets
    attrs = {"RefId": item.comm_object.ets_id}
    channel = channels_by_id.get(item.version.channel_id) if item.version.channel_id else None
    if channel is not None and channel.version.catalog_ref:
        attrs["ChannelId"] = channel.version.catalog_ref
    _put(attrs, "DatapointType", item.version.datapoint_subtype_ets_id)
    _put(attrs, "Text", item.version.text)
    _flag(attrs, "CommunicationFlag", item.version.communication_flag)
    _flag(attrs, "ReadFlag", item.version.read_flag)
    _flag(attrs, "WriteFlag", item.version.write_flag)
    _flag(attrs, "TransmitFlag", item.version.transmit_flag)
    _flag(attrs, "UpdateFlag", item.version.update_flag)
    _flag(attrs, "ReadOnInitFlag", item.version.read_on_init_flag)
    _put(attrs, "Priority", item.version.priority)
    links = links_by_co.get(item.comm_object.id)
    if links:
        attrs["Links"] = " ".join(links)
    SubElement(parent, "ComObjectInstanceRef", attrs)


def _write_channel_instances(
    device_el: Element, snap: InstallationSnapshot, device_id: UUID, inst_ets: str
) -> None:
    rows = [item for item in snap.channels if item.channel.device_id == device_id]
    if not rows:
        return
    parent = SubElement(device_el, "ChannelInstances")
    for item in rows:
        attrs = {"Id": xml_id(inst_ets, item.channel.ets_id)}
        _put(attrs, "Name", item.version.title)
        _put(attrs, "Description", item.version.description)
        _put(attrs, "RefId", item.version.catalog_ref)
        SubElement(parent, "ChannelInstance", attrs)


def _write_group_object_tree(
    device_el: Element, snap: InstallationSnapshot, device_id: UUID
) -> None:
    channels = [item for item in snap.channels if item.channel.device_id == device_id]
    folders = [item for item in snap.folders if item.folder.device_id == device_id]
    if not channels and not folders:
        return
    gos_by_channel: dict[UUID, list[str]] = {}
    gos_by_folder: dict[UUID, list[str]] = {}
    for comm in snap.comm_objects:
        if comm.comm_object.device_id != device_id:
            continue
        if comm.version.channel_id is not None:
            gos_by_channel.setdefault(comm.version.channel_id, []).append(
                comm.comm_object.ets_id
            )
        if comm.version.folder_id is not None:
            gos_by_folder.setdefault(comm.version.folder_id, []).append(
                comm.comm_object.ets_id
            )
    tree = SubElement(device_el, "GroupObjectTree")
    nodes = SubElement(tree, "Nodes")
    children_ch: dict[UUID | None, list[ChannelSnap]] = {}
    for item in channels:
        children_ch.setdefault(item.version.parent_channel_id, []).append(item)
    folders_by_channel: dict[UUID, list[FolderSnap]] = {}
    folders_by_folder: dict[UUID, list[FolderSnap]] = {}
    root_folders: list[FolderSnap] = []
    for item in folders:
        if item.version.parent_channel_id is not None:
            folders_by_channel.setdefault(item.version.parent_channel_id, []).append(item)
        elif item.version.parent_folder_id is not None:
            folders_by_folder.setdefault(item.version.parent_folder_id, []).append(item)
        else:
            root_folders.append(item)

    def write_folder(parent: Element, item: FolderSnap) -> None:
        attrs = {"Type": "Folder", "RefId": item.folder.ets_id}
        gos = gos_by_folder.get(item.folder.id)
        if gos:
            attrs["GroupObjectInstances"] = " ".join(gos)
        node = SubElement(parent, "Node", attrs)
        nested = folders_by_folder.get(item.folder.id)
        if nested:
            nested_nodes = SubElement(node, "Nodes")
            for child in nested:
                write_folder(nested_nodes, child)

    def write_channel(parent: Element, item: ChannelSnap) -> None:
        ref = item.version.catalog_ref or item.channel.ets_id
        attrs = {"Type": "Channel", "RefId": ref}
        gos = gos_by_channel.get(item.channel.id)
        if gos:
            attrs["GroupObjectInstances"] = " ".join(gos)
        node = SubElement(parent, "Node", attrs)
        nested_channels = children_ch.get(item.channel.id, [])
        nested_folders = folders_by_channel.get(item.channel.id, [])
        if nested_channels or nested_folders:
            nested_nodes = SubElement(node, "Nodes")
            for child in nested_channels:
                write_channel(nested_nodes, child)
            for child in nested_folders:
                write_folder(nested_nodes, child)

    for item in children_ch.get(None, []):
        write_channel(nodes, item)
    for item in root_folders:
        write_folder(nodes, item)


def _write_locations(
    installation: Element, snap: InstallationSnapshot, inst_ets: str
) -> None:
    locations_el = SubElement(installation, "Locations")
    by_id = {item.location.id: item for item in snap.locations}
    children: dict[UUID | None, list[LocationSnap]] = {}
    for item in snap.locations:
        parent_id = item.version.parent_location_id
        if parent_id is not None and parent_id not in by_id:
            parent_id = None
        children.setdefault(parent_id, []).append(item)
    functions_by_loc: dict[UUID, list] = {}
    for item in snap.functions:
        if item.version.location_id is not None:
            functions_by_loc.setdefault(item.version.location_id, []).append(item)
    devices_by_loc: dict[UUID, list[DeviceSnap]] = {}
    for item in snap.devices:
        if item.version.location_id is not None:
            devices_by_loc.setdefault(item.version.location_id, []).append(item)
    lines_by_id = {item.line.id: item for item in snap.lines}
    datapoints_by_id = {item.datapoint.id: item for item in snap.datapoints}

    def write_space(parent: Element, item: LocationSnap) -> None:
        attrs = {"Id": xml_id(inst_ets, item.location.ets_id), "Name": item.version.title}
        _put(attrs, "Type", item.version.location_type)
        _put(attrs, "Usage", item.version.usage)
        _put(attrs, "Number", item.version.number)
        _put(attrs, "Description", item.version.description)
        _put(attrs, "Comment", item.version.comment)
        _put(attrs, "CompletionStatus", item.version.completion_status)
        if item.version.default_line_id in lines_by_id:
            line = lines_by_id[item.version.default_line_id]
            attrs["DefaultLine"] = xml_id(inst_ets, line.line.ets_id)
        space = SubElement(parent, "Space", attrs)
        for device in devices_by_loc.get(item.location.id, []):
            SubElement(
                space,
                "DeviceInstanceRef",
                {"RefId": xml_id(inst_ets, device.device.ets_id)},
            )
        for function in functions_by_loc.get(item.location.id, []):
            fn_attrs = {
                "Id": xml_id(inst_ets, function.function.ets_id),
                "Name": function.version.title,
                "Type": function.version.function_type_ets_id,
            }
            _put(fn_attrs, "Description", function.version.description)
            _put(fn_attrs, "Comment", function.version.comment)
            _put(fn_attrs, "CompletionStatus", function.version.completion_status)
            fn_el = SubElement(space, "Function", fn_attrs)
            for edge in snap.function_datapoints:
                if edge.function_id != function.function.id:
                    continue
                datapoint = datapoints_by_id.get(edge.group_address_id)
                if datapoint is None:
                    continue
                ref_attrs = {"RefId": xml_id(inst_ets, datapoint.datapoint.ets_id)}
                if edge.ets_id:
                    ref_attrs["Id"] = xml_id(inst_ets, edge.ets_id)
                _put(ref_attrs, "Role", edge.role)
                SubElement(fn_el, "GroupAddressRef", ref_attrs)
        for child in children.get(item.location.id, []):
            write_space(space, child)

    for item in children.get(None, []):
        write_space(locations_el, item)


def _write_trades(
    installation: Element, snap: InstallationSnapshot, inst_ets: str
) -> None:
    if not snap.trades:
        return
    trades_el = SubElement(installation, "Trades")
    by_id = {item.trade.id: item for item in snap.trades}
    children: dict[UUID | None, list] = {}
    for item in snap.trades:
        parent_id = item.version.parent_trade_id
        if parent_id is not None and parent_id not in by_id:
            parent_id = None
        children.setdefault(parent_id, []).append(item)
    devices_by_id = {item.device.id: item for item in snap.devices}
    devices_by_trade: dict[UUID, list[DeviceSnap]] = {}
    for edge in snap.trade_devices:
        device = devices_by_id.get(edge.device_id)
        if device is not None:
            devices_by_trade.setdefault(edge.trade_id, []).append(device)

    def write_trade(parent: Element, item) -> None:
        attrs = {
            "Id": xml_id(inst_ets, item.trade.ets_id),
            "Name": item.version.name,
        }
        _put(attrs, "Number", item.version.number)
        _put(attrs, "Comment", item.version.comment)
        _put(attrs, "Description", item.version.description)
        _put(attrs, "CompletionStatus", item.version.completion_status)
        trade_el = SubElement(parent, "Trade", attrs)
        for device in devices_by_trade.get(item.trade.id, []):
            SubElement(
                trade_el,
                "DeviceInstanceRef",
                {"RefId": xml_id(inst_ets, device.device.ets_id)},
            )
        for child in children.get(item.trade.id, []):
            write_trade(trade_el, child)

    for item in children.get(None, []):
        write_trade(trades_el, item)


def _merge_xml_fragments(
    installation: Element, snap: InstallationSnapshot, inst_ets: str
) -> None:
    by_id = {inst_ets: installation, xml_id(inst_ets, ""): installation}
    by_id[xml_id(inst_ets, inst_ets)] = installation
    for fragment in snap.contributions.xml:
        parent = by_id.get(fragment.parent_id)
        if parent is None:
            parent = installation
        SubElement(parent, fragment.tag, dict(fragment.attributes))


def _links_by_comm_object(snap: InstallationSnapshot) -> dict[UUID, list[str]]:
    datapoints = {item.datapoint.id: item.datapoint.ets_id for item in snap.datapoints}
    result: dict[UUID, list[str]] = {}
    for edge in snap.comm_object_datapoints:
        ets_id = datapoints.get(edge.group_address_id)
        if ets_id:
            result.setdefault(edge.comm_object_id, []).append(ets_id)
    return result


def _device_address(individual_address: str | None) -> int | None:
    if not individual_address:
        return None
    parts = individual_address.split(".")
    if len(parts) != 3:
        return None
    try:
        return int(parts[2])
    except ValueError:
        return None


def _put(attrs: dict[str, str], name: str, value: str | None) -> None:
    if value is not None and value != "":
        attrs[name] = value


def _flag(attrs: dict[str, str], name: str, value: bool | None) -> None:
    if value is None:
        return
    attrs[name] = "Enabled" if value else "Disabled"


def _xml_bool(value: bool | None) -> str:
    return "true" if value else "false"


def _dump(root: Element) -> str:
    body = tostring(root, encoding="unicode")
    return f'<?xml version="1.0" encoding="utf-8"?>\n{body}\n'
