from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from kss.api.channels import kss_router as channels_kss_router
from kss.api.datapoints import kss_router as datapoints_kss_router
from kss.api.datapoints import read_router as datapoints_read_router
from kss.api.devices import read_router as devices_read_router
from kss.api.flavor import bind_current_lookup, bind_flavor, bind_path_at
from kss.api.folders import kss_router as folders_kss_router
from kss.api.functions import kss_router as functions_kss_router
from kss.api.functions import read_router as functions_read_router
from kss.api.installations import kss_router, read_router
from kss.api.jsonapi import JSONAPIResponse, error_body
from kss.api.locations import read_router as locations_read_router
from kss.api.topology import kss_router as topology_kss_router
from kss.api.trades import kss_router as trades_kss_router

app = FastAPI(title="KSS", description="KNX Semantic Server")

_V1_READ = (
    read_router,
    locations_read_router,
    functions_read_router,
    devices_read_router,
    datapoints_read_router,
)
_KSS_READ = _V1_READ + (
    functions_kss_router,
    topology_kss_router,
    datapoints_kss_router,
    trades_kss_router,
    channels_kss_router,
    folders_kss_router,
)


def _mount(router, prefix: str, *deps) -> None:
    app.include_router(router, prefix=prefix, dependencies=list(deps))


for _router in _V1_READ:
    _mount(
        _router,
        "/api/v1",
        Depends(bind_flavor("v1")),
        Depends(bind_current_lookup),
    )
for _router in _KSS_READ:
    _mount(
        _router,
        "/api/kss",
        Depends(bind_flavor("kss")),
        Depends(bind_current_lookup),
    )
    _mount(
        _router,
        "/api/kss/{at}",
        Depends(bind_flavor("kss")),
        Depends(bind_path_at),
    )
_mount(
    kss_router,
    "/api/kss",
    Depends(bind_flavor("kss")),
    Depends(bind_current_lookup),
)


@app.middleware("http")
async def resolution_header(request: Request, call_next):
    response = await call_next(request)
    if request.method == "GET" and request.url.path.startswith("/api/kss"):
        lookup = getattr(request.state, "lookup", None)
        assumed = bool(lookup and lookup.assumed)
        response.headers["resolution"] = "assumed" if assumed else "exact"
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONAPIResponse:
    del request
    title = {
        400: "Bad Request",
        404: "Not Found",
        405: "Method Not Allowed",
        415: "Unsupported Media Type",
        422: "Unprocessable Entity",
        501: "Not Implemented",
    }.get(exc.status_code, "Error")
    detail = exc.detail if isinstance(exc.detail, str) else title
    return JSONAPIResponse(
        status_code=exc.status_code,
        content=error_body(exc.status_code, title, detail),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONAPIResponse:
    del request
    return JSONAPIResponse(
        status_code=422,
        content=error_body(422, "Unprocessable Entity", str(exc)),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONAPIResponse:
    del request, exc
    return JSONAPIResponse(
        status_code=500,
        content=error_body(500, "Internal Server Error", "Internal Server Error"),
    )
