from unittest import mock

import pytest
import responses

from flash_services.core import Service
from flash_services.tracker import Tracker


@pytest.fixture
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


@responses.activate
def test_get_velocity_success(service):
    responses.add(
        responses.GET,
        'https://www.pivotaltracker.com/services/v5/projects/123/iterations'
        '/456?fields=%3Adefault%2Cvelocity%2Cstories',
        json={
            'velocity': 10,
            'stories': [
                {'current_state': 'foo', 'estimate': 5},
                {'current_state': 'foo'},
            ],
        }
    )

    result = service.details(456)

    assert result == {'velocity': 10, 'stories': {'foo': 5}}
    assert responses.calls[0].request.headers['X-TrackerToken'] == 'foobar'


@mock.patch('flash_services.tracker.logger.debug')
@responses.activate
def test_update_success(debug, service):
    service.current_iteration = 1
    service.project_version = 2
    service._cached = {'foo': 'bar'}
    responses.add(
        responses.GET,
        'https://www.pivotaltracker.com/services/v5/projects/123',
        json={'foo': 'bar', 'current_iteration_number': 0},
        adding_headers={'X-Tracker-Project-Version': '1'},
    )

    result = service.update()

    debug.assert_called_once_with('fetching Tracker project data')
    assert result == {'foo': 'bar'}
    assert responses.calls[0].request.headers['X-TrackerToken'] == 'foobar'


@mock.patch('flash_services.tracker.logger.error')
@responses.activate
def test_get_velocity_failure(error, service):
    responses.add(
        responses.GET,
        'https://www.pivotaltracker.com/services/v5/projects/123/iterations'
        '/456?fields=%3Adefault%2Cvelocity%2Cstories',
        status=401,
    )

    result = service.details(456)

    error.assert_called_once_with('failed to update project iteration details')
    assert result == {}
    assert responses.calls[0].request.headers['X-TrackerToken'] == 'foobar'


@mock.patch('flash_services.tracker.logger.error')
@responses.activate
def test_update_failure(error, service):
    responses.add(
        responses.GET,
        'https://www.pivotaltracker.com/services/v5/projects/123',
        status=401,
    )

    result = service.update()

    error.assert_called_once_with('failed to update Tracker project data')
    assert result == {}
    assert responses.calls[0].request.headers['X-TrackerToken'] == 'foobar'


@mock.patch('flash_services.tracker.logger.debug')
@responses.activate
def test_update_details(debug, service):
    service.current_iteration = 1
    service.project_version = 1
    service._cached = {'foo': 'bar'}
    name = 'foo'
    responses.add(
        responses.GET,
        'https://www.pivotaltracker.com/services/v5/projects/123',
        json={'current_iteration_number': 1, 'name': name},
        adding_headers={'X-Tracker-Project-Version': '2'},
    )
    responses.add(
        responses.GET,
        'https://www.pivotaltracker.com/services/v5/projects/123/iterations'
        '/1?fields=%3Adefault%2Cvelocity%2Cstories',
        json={'velocity': 10, 'stories': []}
    )

    result = service.update()

    debug.assert_has_calls([
        mock.call('fetching Tracker project data'),
        mock.call('project updated, fetching iteration details'),
    ])
    assert result == dict(velocity=10, stories={}, name=name)


@pytest.mark.parametrize('version, iteration, get_details', [
    (1, 1, False),
    (1, 2, True),
    (2, 1, True),
    (2, 2, True),
])
@responses.activate
def test_update_cache(service, version, iteration, get_details):
    name = 'foo'
    responses.add(
        responses.GET,
        'https://www.pivotaltracker.com/services/v5/projects/123',
        adding_headers={'X-Tracker-Project-Version': str(version)},
        json={'current_iteration_number': iteration, 'name': name},
    )
    responses.add(
        responses.GET,
        'https://www.pivotaltracker.com/services/v5/projects/123/iterations'
        '/{}?fields=%3Adefault%2Cvelocity%2Cstories'.format(iteration),
        json={},
    )
    service._cached = {}
    service.current_iteration = 1
    service.project_version = 1

    result = service.update()

    if get_details:
        assert len(responses.calls) == 2
        assert result == dict(name=name, velocity='unknown', stories={})
    else:
        assert len(responses.calls) == 1
        assert result is service._cached
