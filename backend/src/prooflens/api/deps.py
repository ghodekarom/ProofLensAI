"""FastAPI route dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from prooflens.core.config import Settings, get_settings
from prooflens.db.session import get_db_session

SettingsDep = Annotated[Settings, Depends(get_settings)]
DBSessionDep = Annotated[Session, Depends(get_db_session)]
