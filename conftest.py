import pytest
from falcon import testing
import src.web


@pytest.fixture()
def web_app():
    return testing.TestClient(src.web.app)