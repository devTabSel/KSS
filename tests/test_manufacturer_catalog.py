from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kss.models.master import (
    MasterApplicationCommObject,
    MasterApplicationCommObjectRef,
    MasterApplicationProgram,
    MasterHardware,
    MasterHardware2Program,
    MasterProduct,
)
from kss.services.manufacturer_catalog import upsert_manufacturer_catalog

SMALL_MANUFACTURER_CATALOG = {
    "hardware": {
        "M-00A6_H-00000026-1": {
            "knx_id": "M-00A6_H-00000026-1",
            "name": "Enertex KNX DUAL PowerSupply 1280",
            "manufacturer_knx_id": "M-00A6",
        }
    },
    "products": {
        "M-00A6_H-00000026-1_P-1173": {
            "knx_id": "M-00A6_H-00000026-1_P-1173",
            "hardware_knx_id": "M-00A6_H-00000026-1",
            "text": "Enertex KNX Dual PowerSupply 1280",
            "order_number": "1173",
            "manufacturer": "MDT technologies",
        }
    },
    "hardware2programs": {
        "M-00A6_H-00000026-1_HP-0026-10-39D6": {
            "knx_id": "M-00A6_H-00000026-1_HP-0026-10-39D6",
            "hardware_knx_id": "M-00A6_H-00000026-1",
            "application_program_knx_id": "M-00A6_A-0026-10-39D6",
        }
    },
    "application_programs": {
        "M-00A6_A-0026-10-39D6": {
            "knx_id": "M-00A6_A-0026-10-39D6",
            "manufacturer_knx_id": "M-00A6",
            "comm_objects": {
                "O-2": {
                    "knx_id": "O-2",
                    "number": 2,
                    "name": "Zeit",
                    "text": "Last power failure - clock",
                    "function_text": "Status",
                    "object_size": "3 Bytes",
                    "datapoint_type_ref": "DPST-10-1",
                }
            },
            "comm_object_refs": {
                "O-2_R-37": {
                    "knx_id": "O-2_R-37",
                    "comm_object_knx_id": "O-2",
                    "name": None,
                    "text": None,
                    "function_text": None,
                    "object_size": None,
                    "datapoint_type_ref": None,
                }
            },
        }
    },
}


def test_upsert_manufacturer_catalog_is_insert_if_missing(session: Session) -> None:
    upsert_manufacturer_catalog(session, SMALL_MANUFACTURER_CATALOG)

    hardware = session.scalars(select(MasterHardware)).one()
    assert hardware.knx_id == "M-00A6_H-00000026-1"
    assert hardware.name == "Enertex KNX DUAL PowerSupply 1280"
    assert hardware.manufacturer_knx_id == "M-00A6"

    product = session.scalars(select(MasterProduct)).one()
    assert product.order_number == "1173"
    assert product.manufacturer == "MDT technologies"
    assert product.hardware_knx_id == hardware.knx_id

    h2p = session.scalars(select(MasterHardware2Program)).one()
    assert h2p.knx_id == "M-00A6_H-00000026-1_HP-0026-10-39D6"
    assert h2p.application_program_knx_id == "M-00A6_A-0026-10-39D6"

    program = session.scalars(select(MasterApplicationProgram)).one()
    comm_object = session.scalars(select(MasterApplicationCommObject)).one()
    assert comm_object.knx_id == "O-2"
    assert comm_object.function_text == "Status"
    assert comm_object.object_size == "3 Bytes"
    assert comm_object.application_program_id == program.id

    ref = session.scalars(select(MasterApplicationCommObjectRef)).one()
    assert ref.knx_id == "O-2_R-37"
    assert ref.comm_object_id == comm_object.id

    changed = {
        "hardware": {
            "M-00A6_H-00000026-1": {
                "knx_id": "M-00A6_H-00000026-1",
                "name": "should not overwrite",
                "manufacturer_knx_id": "M-00A6",
            }
        },
        "products": {
            "M-00A6_H-00000026-1_P-1173": {
                "knx_id": "M-00A6_H-00000026-1_P-1173",
                "hardware_knx_id": "M-00A6_H-00000026-1",
                "text": "changed",
                "order_number": "9999",
                "manufacturer": "Other",
            }
        },
        "hardware2programs": {},
        "application_programs": {},
    }
    upsert_manufacturer_catalog(session, changed)
    assert session.scalars(select(MasterHardware)).one().name == (
        "Enertex KNX DUAL PowerSupply 1280"
    )
    product = session.scalars(select(MasterProduct)).one()
    assert product.order_number == "1173"
    assert product.manufacturer == "MDT technologies"
    assert session.scalar(select(func.count()).select_from(MasterHardware)) == 1
    assert session.scalar(select(func.count()).select_from(MasterProduct)) == 1


def test_missing_manufacturer_data_skips(session: Session) -> None:
    upsert_manufacturer_catalog(session, None)
    upsert_manufacturer_catalog(session, "nope")
    assert session.scalar(select(func.count()).select_from(MasterHardware)) == 0


def test_product_without_parent_hardware_is_skipped(session: Session) -> None:
    upsert_manufacturer_catalog(
        session,
        {
            "hardware": {},
            "products": {
                "M-00A6_H-missing_P-1": {
                    "knx_id": "M-00A6_H-missing_P-1",
                    "hardware_knx_id": "M-00A6_H-missing",
                    "order_number": "1",
                    "manufacturer": "MDT",
                }
            },
            "hardware2programs": {},
            "application_programs": {},
        },
    )
    assert session.scalar(select(func.count()).select_from(MasterProduct)) == 0


def test_incomplete_rows_are_skipped(session: Session) -> None:
    upsert_manufacturer_catalog(
        session,
        {
            "hardware": {
                "good": {
                    "knx_id": "M-00A6_H-00000026-1",
                    "name": "PSU",
                    "manufacturer_knx_id": "M-00A6",
                },
                "bad": {"name": "no knx_id", "manufacturer_knx_id": "M-00A6"},
            },
            "products": {},
            "hardware2programs": {},
            "application_programs": {
                "M-00A6_A-0026-10-39D6": {
                    "knx_id": "M-00A6_A-0026-10-39D6",
                    "manufacturer_knx_id": "M-00A6",
                    "comm_objects": {
                        "O-2": {"knx_id": "O-2", "number": 2},
                        "bad": {"number": 3},
                    },
                    "comm_object_refs": {
                        "O-2_R-1": {
                            "knx_id": "O-2_R-1",
                            "comm_object_knx_id": "O-2",
                        },
                        "missing": {"comm_object_knx_id": "O-2"},
                    },
                }
            },
        },
    )
    assert session.scalars(select(MasterHardware)).one().knx_id == "M-00A6_H-00000026-1"
    assert session.scalars(select(MasterApplicationCommObject)).one().knx_id == "O-2"
    assert session.scalars(select(MasterApplicationCommObjectRef)).one().knx_id == (
        "O-2_R-1"
    )
