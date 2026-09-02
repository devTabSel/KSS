"""Parse .knxproj files via the xknxproject fork."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from xknxproject import XKNXProj
from xknxproject.exceptions import XknxProjectException
from xknxproject.models import KNXProject, ProjectInfo


class KnxprojImportError(ValueError):
    """Rejected knxproj ingest (unknown format, schema, or parse failure)."""


def parse_ets_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    if "." in text:
        head, rest = text.split(".", 1)
        digits = ""
        suffix = ""
        for index, char in enumerate(rest):
            if char.isdigit():
                digits += char
            else:
                suffix = rest[index:]
                break
        text = f"{head}.{digits[:6]}{suffix}"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def parse_knxproj(path: Path, password: str | None = None) -> KNXProject:
    try:
        return XKNXProj(path, password=password).parse(combine=False)
    except XknxProjectException as exc:
        raise KnxprojImportError(str(exc) or "failed to parse knxproj") from exc


def project_info(project: KNXProject) -> ProjectInfo:
    return project["info"]
