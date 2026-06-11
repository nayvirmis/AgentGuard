import os

import pytest

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["AUTH_MODE"] = "development"
os.environ["LLM_PROVIDER"] = "fake"

from backend.app.config import get_settings
from backend.app.db import Base, engine


@pytest.fixture(autouse=True)
def clean_database():
    get_settings.cache_clear()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
