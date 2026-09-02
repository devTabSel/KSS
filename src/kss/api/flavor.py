from typing import Annotated, Literal

from fastapi import Depends, Request

Flavor = Literal["v1", "kss"]


def bind_flavor(flavor: Flavor):
    def _set(request: Request) -> None:
        request.state.api_flavor = flavor

    return _set


def extra_from_request(request: Request) -> bool:
    return getattr(request.state, "api_flavor", "v1") == "kss"


ExtraDep = Annotated[bool, Depends(extra_from_request)]
