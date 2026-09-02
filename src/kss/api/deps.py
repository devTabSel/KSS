from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from kss.db import get_session

SessionDep = Annotated[Session, Depends(get_session)]


def _page_number(
    page_number: Annotated[int, Query(ge=0, alias="page[number]")] = 0,
) -> int:
    return page_number


def _page_size(
    page_size: Annotated[int, Query(ge=1, alias="page[size]")] = 65536,
) -> int:
    return page_size


PageNumber = Annotated[int, Depends(_page_number)]
PageSize = Annotated[int, Depends(_page_size)]
