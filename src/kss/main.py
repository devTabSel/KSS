from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from kss.api.flavor import bind_flavor
from kss.api.installations import kss_router, read_router
from kss.api.jsonapi import JSONAPIResponse, error_body

app = FastAPI(title="KSS", description="KNX Semantic Server")
app.include_router(
    read_router,
    prefix="/api/v1",
    dependencies=[Depends(bind_flavor("v1"))],
)
app.include_router(
    read_router,
    prefix="/api/kss",
    dependencies=[Depends(bind_flavor("kss"))],
)
app.include_router(
    kss_router,
    prefix="/api/kss",
    dependencies=[Depends(bind_flavor("kss"))],
)


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
