import jinja2
import os
import pytest


@pytest.fixture
def jinja():
    here = os.path.dirname(__file__)
    template_path = '{}/flash_services/templates'.format(here)
    return jinja2.Environment(loader=jinja2.FileSystemLoader(template_path))
