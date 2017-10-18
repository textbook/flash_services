from datetime import datetime
from unittest import mock
from urllib.parse import quote_plus

from freezegun import freeze_time
import pytest
import responses

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


@mock.patch('flash_services.jenkins.logger.debug')
@responses.activate
def test_update_success(debug, service, url):
    responses.add(
        responses.GET,
        url,
        headers={'Authorization': 'Basic Zm9vOmJhcg=='},
        json={'builds': [], 'name': 'baz'},
    )

    result = service.update()

    debug.assert_called_once_with('fetching Jenkins project data')
    assert result == {'builds': [], 'name': 'baz', 'health': 'neutral'}


@mock.patch('flash_services.jenkins.logger.error')
@responses.activate
def test_update_failure(error, service, url):
    responses.add(responses.GET, url, status=401)

    result = service.update()

    error.assert_called_once_with('failed to update Jenkins project data')
    assert result == {}


@responses.activate
def test_formatting(service, url):
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
    responses.add(responses.GET, url, json=response)

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


@responses.activate
def test_aborted_formatting(service, url):
    response = dict(
        name='job',
        builds=[dict(
            duration=1234,
            description=None,
            timestamp=1481387964313,
            result='ABORTED',
        )],
    )
    responses.add(responses.GET, url, json=response)

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


@responses.activate
@freeze_time(datetime.fromtimestamp(1481387969.3))
def test_unfinished_formatting(service, url):
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
    responses.add(responses.GET, url, json=response)

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
@responses.activate
def test_estimated_formatting(service, url):
    response = dict(name='foo', builds=[
        dict(duration=0, description=None, timestamp=1481387964313, result=None),
        dict(duration=10000, description=None, timestamp=1481387964313, result='SUCCESS'),
        dict(duration=10000, description=None, timestamp=1481387964313, result='SUCCESS'),
        dict(duration=10000, description=None, timestamp=1481387964313, result='SUCCESS'),
        dict(duration=10000, description=None, timestamp=1481387964313, result='SUCCESS'),
        dict(duration=10000, description=None, timestamp=1481387964313, result='SUCCESS'),
    ])
    responses.add(responses.GET, url, json=response)

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
