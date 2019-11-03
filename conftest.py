import jinja2
import os
import pytest
import responses


@pytest.fixture
def jinja():
    here = os.path.dirname(__file__)
    template_path = '{}/flash_services/templates'.format(here)
    return jinja2.Environment(loader=jinja2.FileSystemLoader(template_path))


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock() as requests_mock:
        yield requests_mock
