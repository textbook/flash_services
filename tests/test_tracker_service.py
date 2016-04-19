from unittest import mock

import pytest

from flash_services.core import Service
from flash_services.tracker import Tracker


@pytest.fixture()
def service():
    return Tracker(api_token='foobar', project_id=123)


def test_tracker_service_type():
    assert issubclass(Tracker, Service)


def test_correct_config():
    assert Tracker.TEMPLATE == 'tracker-section'
    assert Tracker.REQUIRED == {'api_token', 'project_id'}
    assert Tracker.ROOT == 'https://www.pivotaltracker.com/services/v5'


def test_headers(service):
    assert service.headers == {'X-TrackerToken': 'foobar'}


@mock.patch('flash_services.tracker.requests.get', **{
    'return_value.status_code': 200,
    'return_value.json.return_value': {
        'velocity': 10,
        'stories': [
            {'current_state': 'foo', 'estimate': 5},
            {'current_state': 'foo'},
        ],
    },
})
def test_get_velocity_success(get, service):
    result = service.details(456)

    get.assert_called_once_with(
        ('https://www.pivotaltracker.com/services/v5/projects/123/'
         'iterations/456?fields=%3Adefault%2Cvelocity%2Cstories'),
        headers={'X-TrackerToken': 'foobar'},
    )
    assert result == {'velocity': 10, 'stories': {'foo': 5}}


@mock.patch('flash_services.tracker.logger.debug')
@mock.patch('flash_services.tracker.requests.get', **{
    'return_value.status_code': 200,
    'return_value.headers': {'X-Tracker-Project-Version': '1'},
    'return_value.json.return_value': {'foo': 'bar', 'current_iteration_number': 0},
})
def test_update_success(get, debug, service):
    service.current_iteration = 1
    service.project_version = 2
    service._cached = {'foo': 'bar'}

    result = service.update()

    get.assert_called_once_with(
        'https://www.pivotaltracker.com/services/v5/projects/123',
        headers={'X-TrackerToken': 'foobar'},
    )
    debug.assert_called_once_with('fetching Tracker project data')
    assert result == {'foo': 'bar'}


@mock.patch('flash_services.tracker.logger.error')
@mock.patch('flash_services.tracker.requests.get', **{
    'return_value.status_code': 401,
})
def test_get_velocity_failure(get, error, service):
    result = service.details(456)

    get.assert_called_once_with(
        ('https://www.pivotaltracker.com/services/v5/projects/123/'
         'iterations/456?fields=%3Adefault%2Cvelocity%2Cstories'),
        headers={'X-TrackerToken': 'foobar'},
    )
    assert result == {}
    error.assert_called_once_with('failed to update project iteration details')


@mock.patch('flash_services.tracker.logger.error')
@mock.patch('flash_services.tracker.requests.get', **{
    'return_value.status_code': 401,
})
def test_update_failure(get, error, service):
    result = service.update()

    get.assert_called_once_with(
        'https://www.pivotaltracker.com/services/v5/projects/123',
        headers={'X-TrackerToken': 'foobar'},
    )
    error.assert_called_once_with('failed to update Tracker project data')
    assert result == {}


@mock.patch('flash_services.tracker.logger.debug')
@mock.patch('flash_services.tracker.requests.get', **{
    'return_value.status_code': 200,
    'return_value.headers': {'X-Tracker-Project-Version': '2'},
    'return_value.json.return_value': {'current_iteration_number': 1},
})
@mock.patch.object(Tracker, 'details')
def test_update_details(details, get, debug, service):
    service.current_iteration = 1
    service.project_version = 1
    service._cached = {'foo': 'bar'}

    service.update()

    details.assert_called_once_with(1)
    debug.assert_has_calls([
        mock.call('fetching Tracker project data'),
        mock.call('project updated, fetching iteration details'),
    ])


@pytest.mark.parametrize('version, iteration, get_details', [
    (1, 1, False),
    (1, 2, True),
    (2, 1, True),
    (2, 2, True),
])
@mock.patch('flash_services.tracker.requests.get', **{
    'return_value.status_code': 200,
})
@mock.patch.object(Tracker, 'details')
def test_update_cache(details, get, service, version, iteration, get_details):
    get.configure_mock(**{
        'return_value.headers': {'X-Tracker-Project-Version': version},
        'return_value.json.return_value': {'current_iteration_number': iteration},
    })
    service._cached = {}
    service.current_iteration = 1
    service.project_version = 1

    result = service.update()

    if get_details:
        details.assert_called_once_with(iteration)
    else:
        details.assert_not_called()
        assert result is service._cached
