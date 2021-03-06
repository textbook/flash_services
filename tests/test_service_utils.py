import logging
from datetime import datetime, timedelta

import pytest

from flash_services.utils import (elapsed_time, estimate_time, friendlier,
                                  health_summary, occurred, required_args,
                                  remove_tags)

TWO_DAYS_AGO = datetime.now() - timedelta(days=2, hours=12)


@pytest.mark.parametrize('input_, expected, logged', [
    ((None,), 'time not available', True),
    ((TWO_DAYS_AGO.strftime('%Y-%m-%dT%H:%M:%SZ'),), 'two days ago', False),
    ((TWO_DAYS_AGO.strftime('%Y-%m-%dT%H:%M:%S'),), 'two days ago', False),
])
def test_occurred(input_, expected, logged, caplog):
    assert occurred(*input_) == expected
    if logged:
        assert 'failed to parse occurrence time None' in [
            record.getMessage()
            for record in caplog.records
            if record.levelno == logging.WARN
        ]
    else:
        assert caplog.records == []


@pytest.mark.parametrize('input_, expected, logged', [
    ((None, None), (None, None, 'elapsed time not available'), True),
    (
        ('2011-12-13T14:15:16', None),
        (1323785716, None, 'elapsed time not available'),
        True,
    ),
    (
        (None, '2011-12-13T14:15:16'),
        (None, 1323785716, 'elapsed time not available'),
        True,
    ),
    (
        ('2011-12-11T02:15:16', '2011-12-13T14:15:16'),
        (1323569716, 1323785716, 'took two days'),
        False,
    ),
])
def test_elapsed_time(input_, expected, logged, caplog):
    assert elapsed_time(*input_) == expected
    if logged:
        assert 'failed to generate elapsed time' in [
            record.getMessage()
            for record in caplog.records
            if record.levelno == logging.WARN
        ]
    else:
        assert caplog.records == []


@pytest.mark.parametrize('text, expected', [
    ('this contains 1, 10 and 100', 'this contains one, ten and 100'),
    ('this contains 6', 'this contains six'),
    ('1', 'one'),
    ('11', '11'),
])
def test_numeric_words(text, expected):
    assert friendlier(lambda s: s)(text) == expected


@pytest.mark.parametrize('builds, health', [
    ([{'outcome': 'passed'}], 'ok'),
    ([{'outcome': 'working'}, {'outcome': 'passed'}], 'ok'),
    ([{'outcome': 'failed'}], 'error'),
    ([{'outcome': 'working'}], 'neutral'),
])
def test_health_summary(builds, health):
    assert health_summary(builds) == health


def test_build_estimate_unstarted():
    current = {'started_at': None, 'outcome': 'working'}

    estimate_time([current])

    assert current['elapsed'] == 'estimate not available'


def test_build_estimate_no_history():
    current = {'started_at': 123456789, 'outcome': 'working'}

    estimate_time([current])

    assert current['elapsed'] == 'estimate not available'


def test_build_estimate_usable():
    builds = [
        {'started_at': int(datetime.now().timestamp()), 'outcome': 'working'},
        {'outcome': 'passed', 'duration': 610},
        {'outcome': 'passed', 'duration': 600},
        {'outcome': 'passed', 'duration': 605},
    ]

    estimate_time(builds)

    assert builds[0]['elapsed'] == 'ten minutes left'


def test_build_estimate_negative():
    builds = [
        {'started_at': int(datetime.now().timestamp()), 'outcome': 'working'},
        {'outcome': 'passed', 'duration': -5},
        {'outcome': 'passed', 'duration': -10},
        {'outcome': 'passed', 'duration': 0},
    ]

    estimate_time(builds)

    assert builds[0]['elapsed'] == 'nearly done'


def test_build_estimate_not_first():
    builds = [
        {'started_at': None, 'outcome': None},
        {'started_at': int(datetime.now().timestamp()), 'outcome': 'working'},
        {'outcome': 'passed', 'duration': -5},
        {'outcome': 'passed', 'duration': -10},
        {'outcome': 'passed', 'duration': 0},
    ]

    estimate_time(builds)

    assert builds[1]['elapsed'] == 'nearly done'


@pytest.mark.parametrize('message, expected', [
    ('[#123456789] hello world', 'hello world'),
    ('[#123456789 #234567] hello world', 'hello world'),
    ('[#123456789 fixed #234567] hello world', 'hello world'),
    ('[FINISHES #123456789] hello world', 'hello world'),
    ('hello world Fixes foo/bar#123', 'hello world'),
])
def test_remove_tags(message, expected):
    assert remove_tags(message) == expected


@pytest.mark.parametrize('attrs, expected', [
    ({}, set()),
    ({'__init__': lambda self, *, foo, bar: None}, {'foo', 'bar'}),
    ({'__init__': lambda self, *, foo, bar=None: None}, {'foo'}),
    ({'REQUIRED': {'baz'}}, {'baz'}),
    ({'REQUIRED': {'baz'}, '__init__': lambda self, *, foo: None}, {'foo', 'baz'}),
])
def test_required_args(attrs, expected):
    assert required_args(attrs) == expected
