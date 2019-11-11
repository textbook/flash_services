import logging
from datetime import datetime
from urllib.parse import quote_plus

import pytest
import responses
from freezegun import freeze_time

from flash_services import Jenkins, SERVICES

ROOT = 'https://test.org'
JOB = 'baz'


@pytest.fixture
def service():
    return SERVICES['jenkins'](
        username='foo',
        password='bar',
        root=ROOT,
        job=JOB,
    )


@pytest.fixture
def url():
    return '{}/job/{}/api/json?tree={}'.format(
        ROOT,
        JOB,
        quote_plus(Jenkins.TREE_PARAMS),
    )


def test_correct_config():
    assert Jenkins.REQUIRED == {'username', 'password', 'root', 'job'}
    assert Jenkins.TEMPLATE == 'ci-section'


def test_update_success(service, url, caplog, mocked_responses):
    caplog.set_level(logging.DEBUG)
    mocked_responses.add(
        responses.GET,
        url,
        headers={'Authorization': 'Basic Zm9vOmJhcg=='},
        json={'builds': [], 'name': 'baz'},
    )

    result = service.update()

    assert 'fetching Jenkins project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    assert result == {'builds': [], 'name': 'baz', 'health': 'neutral'}


def test_update_failure(service, url, caplog, mocked_responses):
    mocked_responses.add(responses.GET, url, status=401)

    result = service.update()

    assert 'failed to update Jenkins project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.ERROR
    ]
    assert result == {}


def test_formatting(service, url, mocked_responses):
    response = dict(name='job', builds=[
        dict(
            duration=31698,
            description=None,
            timestamp=1481387964313,
            result='SUCCESS',
            changeSets=[
                dict(items=[dict(comment='hello', author=dict(fullName='foo'))]),
                dict(items=[dict(comment='world', author=dict(fullName='bar'))]),
                dict(items=[dict(comment='again', author=dict(fullName='baz'))]),
            ]
        )
    ])
    mocked_responses.add(responses.GET, url, json=response)

    result = service.update()

    assert result == dict(
        name='job',
        builds=[dict(
            author='baz',
            duration=31,
            elapsed='took 31 seconds',
            message='again',
            outcome='passed',
            started_at=1481387964,
        )],
        health='ok',
    )


def test_aborted_formatting(service, url, mocked_responses):
    response = dict(
        name='job',
        builds=[dict(
            duration=1234,
            description=None,
            timestamp=1481387964313,
            result='ABORTED',
        )],
    )
    mocked_responses.add(responses.GET, url, json=response)

    result = service.update()

    assert result == dict(
        name='job',
        builds=[dict(
            author='<no author>',
            duration=1,
            elapsed='took a second',
            message='<no message>',
            outcome='cancelled',
            started_at=1481387964,
        )],
        health='neutral',
    )


@freeze_time(datetime.fromtimestamp(1481387969.3))
def test_unfinished_formatting(service, url, mocked_responses):
    response = dict(
        name='foo',
        builds=[dict(
            building=True,
            duration=0,
            description=None,
            timestamp=1481387964313,
            result='SUCCESS',
            changeSets=[],
        )],
    )
    mocked_responses.add(responses.GET, url, json=response)

    result = service.update()

    assert result == dict(
        name='foo',
        builds=[dict(
            author='<no author>',
            duration=5,
            elapsed='estimate not available',
            message='<no message>',
            outcome='working',
            started_at=1481387964,
        )],
        health='neutral',
    )


@freeze_time(datetime.fromtimestamp(1481387969))
def test_estimated_formatting(service, url, mocked_responses):
    response = dict(name='foo', builds=[
        dict(duration=0, description=None, timestamp=1481387964313, result=None),
        dict(duration=10000, description=None, timestamp=1481387964313, result='SUCCESS'),
        dict(duration=10000, description=None, timestamp=1481387964313, result='SUCCESS'),
        dict(duration=10000, description=None, timestamp=1481387964313, result='SUCCESS'),
        dict(duration=10000, description=None, timestamp=1481387964313, result='SUCCESS'),
        dict(duration=10000, description=None, timestamp=1481387964313, result='SUCCESS'),
    ])
    mocked_responses.add(responses.GET, url, json=response)

    result = service.update()

    assert len(result['builds']) == 4
    assert result['builds'][0] == dict(
        author='<no author>',
        duration=5,
        elapsed='five seconds left',
        message='<no message>',
        outcome='working',
        started_at=1481387964,
    )
