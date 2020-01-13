import pytest
import boto3
from falcon import testing
from botocore.stub import Stubber
import src.web


@pytest.fixture()
def web_app():
    return testing.TestClient(src.web.app)


@pytest.fixture(autouse=True)
def s3_stub():
    s3_resource = boto3.resource('s3')
    with Stubber(s3_resource.meta.client) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()