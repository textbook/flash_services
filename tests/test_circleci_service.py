import logging
import pytest
import responses

from flash_services.circleci import CircleCI
from flash_services.core import ContinuousIntegrationService


@pytest.fixture
def service():
    return CircleCI(
        api_token='banana',
        vcs_type='foo',
        username='bar',
        project='baz',
        branch='qux'
    )


def test_service_type():
    assert issubclass(CircleCI, ContinuousIntegrationService)


def test_update_success(service, caplog, mocked_responses):
    caplog.set_level(logging.DEBUG)
    mocked_responses.add(
        responses.GET,
        'https://circleci.com/api/v1.1/project/foo/bar/baz/tree/qux?limit=100&shallow=true',
        json=[]
    )

    result = service.update()

    assert 'fetching CircleCI project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    assert result == {'builds': [], 'name': 'foo/bar/baz [qux]', 'health': 'neutral'}
    assert mocked_responses.calls[0].request.headers['Accept'] == 'application/json'
    assert mocked_responses.calls[0].request.headers['Circle-Token'] == 'banana'
