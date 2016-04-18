"""Useful utility functions for services."""

from datetime import datetime, timezone
import logging
import re

from dateutil.parser import parse
from humanize import naturaldelta, naturaltime

logger = logging.getLogger(__name__)

WORDS = {'1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five',
         '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine', '10': 'ten'}

NUMBERS = re.compile(r'\b([1-9]|10)\b')


def _numeric_words(text):
    """Replace numbers 1-10 with words.

    Arguments:
      text (:py:class:`str`): The text to replace numbers in.

    Returns:
      :py:class:`str`: The new text containing words.

    """
    return NUMBERS.sub(lambda m: WORDS[m.group()], text)


def friendlier(func):
    """Replace numbers to make functions friendlier.

    Arguments:
      func: The function to wrap.

    Returns:
      A wrapper function applying :py:func:`_numeric_words`.

    """
    def wrapper(*args, **kwargs):
        """Wrapper function to apply _numeric_words."""
        result = func(*args, **kwargs)
        try:
            return _numeric_words(result)
        except TypeError:
            return result
    return wrapper

naturaldelta = friendlier(naturaldelta)
naturaltime = friendlier(naturaltime)


def truncate(text, max_len=20):
    """Truncate the supplied text.

    Arguments:
      text (:py:class:`str`): The text to truncate.
      max_len (:py:class:`int`, optional): The maximum text length to
        return (defaults to ``20``).

    """
    if len(text) <= max_len:
        return text
    return '{}...'.format(text[:(max_len - 3)].strip())


def elapsed_time(start, end):
    """Calculate the elapsed time for a service activity.

    Arguments:
      start (:py:class:`str`): The activity start time.
      end (:py:class:`str`): The activity end time.

    Returns:
      :py:class:`tuple`: The start and end times and humanized elapsed
        time.

    """
    start_time = safe_parse(start)
    end_time = safe_parse(end)
    if start_time is None or end_time is None:
        logger.exception('failed to generate elapsed time')
        text = 'elapsed time not available'
    else:
        text = 'took {}'.format(naturaldelta(parse(end) - parse(start)))
    return to_utc_timestamp(start_time), to_utc_timestamp(end_time), text


def to_utc_timestamp(date_time):
    """Convert a naive or timezone-aware datetime to UTC timestamp.

    Arguments:
      date_time (:py:class:`datetime.datetime`): The datetime to
        convert.

    Returns:
      :py:class:`int`: The timestamp (in seconds).

    """
    if date_time is None:
        return
    if date_time.tzname is None:
        timestamp = date_time.replace(tzinfo=timezone.utc).timestamp()
    else:
        timestamp = date_time.timestamp()
    return int(round(timestamp, 0))


def safe_parse(time):
    """Parse a string without throwing an error.

    Arguments:
      time (:py:class:`str`): The string to parse.

    Returns:
      :py:class:`datetime.datetime`: The parsed datetime.

    """
    if time is None:
        return
    try:
        return parse(time)
    except (OverflowError, ValueError):
        pass


def occurred(at_):
    """Calculate when a service event occurred.

    Arguments:
      at_ (:py:class:`str`): When the event occurred.

    Returns:
      :py:class:`str`: The humanized occurrence time.

    """
    try:
        occurred_at = parse(at_)
    except (AttributeError, ValueError):
        logger.exception('failed to parse occurrence time')
        return 'time not available'
    utc_now = datetime.now(tz=timezone.utc)
    try:
        return naturaltime((utc_now - occurred_at).total_seconds())
    except TypeError:  # at_ is a naive datetime
        return naturaltime((datetime.now() - occurred_at).total_seconds())


def health_summary(builds):
    """Summarise the health of a project based on builds.

    Arguments:
      builds (:py:class:`list`): List of builds.

    Returns:
      :py:class:`str`: The health summary.

    """
    for build in builds:
        if build['outcome'] == 'passed':
            return 'ok'
        elif build['outcome'] in ['failed', 'crashed']:
            return 'error'
        else:
            continue
    return 'neutral'


def estimate_time(builds):
    """Update the working build with an estimated completion time.

    Takes a simple average over the previous builds, using those
    whose outcome is ``'passed'``.

    Arguments:
      builds (:py:class:`list`): All builds.

    """
    try:
        index, current = next(
            (index, build) for index, build in enumerate(builds[:4])
            if build['outcome'] == 'working'
        )
    except StopIteration:
        return  # no in-progress builds
    if current.get('started_at') is None:
        current['elapsed'] = 'estimate not available'
        return
    usable = [
        current for current in builds[index + 1:]
        if current['outcome'] == 'passed' and current['duration'] is not None
    ]
    if not usable:
        current['elapsed'] = 'estimate not available'
        return
    average_duration = int(sum(build['duration'] for build in usable) /
                           float(len(usable)))
    finish = current['started_at'] + average_duration
    remaining = (datetime.fromtimestamp(finish) -
                 datetime.now()).total_seconds()
    if remaining >= 0:
        current['elapsed'] = '{} left'.format(naturaldelta(remaining))
    else:
        current['elapsed'] = 'nearly done'
