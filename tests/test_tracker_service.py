import logging

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


def test_get_velocity_success(service, mocked_responses):
    mocked_responses.add(
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
    assert mocked_responses.calls[0].request.headers['X-TrackerToken'] == 'foobar'


def test_update_success(service, caplog, mocked_responses):
    caplog.set_level(logging.DEBUG)
    service.current_iteration = 1
    service.project_version = 2
    service._cached = {'foo': 'bar'}
    mocked_responses.add(
        responses.GET,
        'https://www.pivotaltracker.com/services/v5/projects/123',
        json={'foo': 'bar', 'current_iteration_number': 0},
        adding_headers={'X-Tracker-Project-Version': '1'},
    )

    result = service.update()

    assert 'fetching Tracker project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    assert result == {'foo': 'bar'}
    assert mocked_responses.calls[0].request.headers['X-TrackerToken'] == 'foobar'


def test_get_velocity_failure(service, caplog, mocked_responses):
    mocked_responses.add(
        responses.GET,
        'https://www.pivotaltracker.com/services/v5/projects/123/iterations'
        '/456?fields=%3Adefault%2Cvelocity%2Cstories',
        status=401,
    )

    result = service.details(456)

    assert 'failed to update project iteration details' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.ERROR
    ]
    assert result == {}
    assert mocked_responses.calls[0].request.headers['X-TrackerToken'] == 'foobar'


def test_update_failure(service, caplog, mocked_responses):
    mocked_responses.add(
        responses.GET,
        'https://www.pivotaltracker.com/services/v5/projects/123',
        status=401,
    )

    result = service.update()

    assert 'failed to update Tracker project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.ERROR
    ]
    assert result == {}
    assert mocked_responses.calls[0].request.headers['X-TrackerToken'] == 'foobar'


def test_update_details(service, caplog, mocked_responses):
    caplog.set_level(logging.DEBUG)
    service.current_iteration = 1
    service.project_version = 1
    service._cached = {'foo': 'bar'}
    name = 'foo'
    mocked_responses.add(
        responses.GET,
        'https://www.pivotaltracker.com/services/v5/projects/123',
        json={'current_iteration_number': 1, 'name': name},
        adding_headers={'X-Tracker-Project-Version': '2'},
    )
    mocked_responses.add(
        responses.GET,
        'https://www.pivotaltracker.com/services/v5/projects/123/iterations'
        '/1?fields=%3Adefault%2Cvelocity%2Cstories',
        json={'velocity': 10, 'stories': []}
    )

    result = service.update()

    debug_logs = [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    assert 'fetching Tracker project data' in debug_logs
    assert 'project updated, fetching iteration details' in debug_logs
    assert result == dict(velocity=10, stories={}, name=name)


@pytest.mark.parametrize('version, iteration, get_details', [
    (1, 1, False),
    (1, 2, True),
    (2, 1, True),
    (2, 2, True),
])
def test_update_cache(service, version, iteration, get_details, mocked_responses):
    name = 'foo'
    mocked_responses.add(
        responses.GET,
        'https://www.pivotaltracker.com/services/v5/projects/123',
        adding_headers={'X-Tracker-Project-Version': str(version)},
        json={'current_iteration_number': iteration, 'name': name},
    )
    if get_details:
        mocked_responses.add(
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
        assert len(mocked_responses.calls) == 2
        assert result == dict(name=name, velocity='unknown', stories={})
    else:
        assert len(mocked_responses.calls) == 1
        assert result is service._cached
