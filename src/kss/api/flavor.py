from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException

from kss.services.knxproj import parse_ets_datetime
from kss.services.temporal import activate_lookup, begin_lookup, isoformat_utc

Flavor = Literal["v1", "kss"]

API_BASE: dict[Flavor, str] = {"v1": "/api/v1", "kss": "/api/kss"}


class _LookupRoute(APIRoute):
    """Re-bind the request Lookup into this task before the sync handler runs."""

    def get_route_handler(self):
        inner = super().get_route_handler()

        async def handler(request: Request):
            lookup = getattr(request.state, "lookup", None)
            if lookup is not None:
                activate_lookup(lookup)
            return await inner(request)

        return handler


def bind_flavor(flavor: Flavor):
    def _set(request: Request) -> None:
        request.state.api_flavor = flavor

    return _set


def _resolution_allows_assumed(request: Request) -> bool:
    if getattr(request.state, "api_flavor", "v1") != "kss":
        return False
    if request.method != "GET":
        return True
    raw = request.headers.get("resolution")
    if raw is None:
        return True
    value = raw.strip().lower()
    if value == "assumed":
        return True
    if value == "exact":
        return False
    raise StarletteHTTPException(status_code=422, detail="invalid resolution")


async def bind_current_lookup(request: Request) -> None:
    request.state.lookup = begin_lookup(
        None, allow_assumed=_resolution_allows_assumed(request)
    )
    request.state.at = None


async def bind_path_at(request: Request) -> None:
    raw = request.path_params.get("at")
    if not raw:
        raise StarletteHTTPException(status_code=422, detail="invalid at")
    try:
        parsed = parse_ets_datetime(raw)
    except (TypeError, ValueError):
        parsed = None
    if parsed is None:
        raise StarletteHTTPException(status_code=422, detail="invalid at")
    request.state.lookup = begin_lookup(
        parsed, allow_assumed=_resolution_allows_assumed(request)
    )
    request.state.at = parsed


def extra_from_request(request: Request) -> bool:
    return getattr(request.state, "api_flavor", "v1") == "kss"


def flavor_from_request(request: Request) -> Flavor:
    flavor = getattr(request.state, "api_flavor", "v1")
    return "kss" if flavor == "kss" else "v1"


def at_path_token(value: datetime) -> str:
    return quote(isoformat_utc(value), safe="")


def api_base_from_request(request: Request) -> str:
    base = API_BASE[flavor_from_request(request)]
    at = getattr(request.state, "at", None)
    if at is not None:
        return f"{base}/{at_path_token(at)}"
    return base


ExtraDep = Annotated[bool, Depends(extra_from_request)]
ApiBaseDep = Annotated[str, Depends(api_base_from_request)]


def api_router() -> APIRouter:
    return APIRouter(route_class=_LookupRoute)
