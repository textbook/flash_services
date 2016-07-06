"""Core service description."""

from abc import ABCMeta, abstractmethod
from datetime import datetime
from datetime import timezone
from html import escape, unescape
import logging
from urllib.parse import urlencode

from dateutil.parser import parse

from .utils import remove_tags

logger = logging.getLogger(__name__)


class Service(metaclass=ABCMeta):
    """Abstract base class for services."""

    FRIENDLY_NAME = escape('<unnamed>')
    """:py:class:`str`: The friendly name of the service."""

    REQUIRED = set()
    """:py:class:`set`: The service's required configuration keys."""

    ROOT = ''
    """:py:class:`str`: The root URL for the service API."""

    TEMPLATE = 'undefined-section'
    """:py:class:`str`: The name of the template to render."""

    @abstractmethod
    def __init__(self, *_, **kwargs):
        self.service_name = kwargs.get('name')

    @abstractmethod
    def update(self):
        """Get the current state to display on the dashboard."""
        raise NotImplementedError

    @property
    def headers(self):
        """Get the headers for the service requests."""
        return {}

    def url_builder(self, endpoint, *, root=None, params=None, url_params=None):
        """Create a URL for the specified endpoint.

        Arguments:
          endpoint (:py:class:`str`): The API endpoint to access.
          root: (:py:class:`str`, optional): The root URL for the
            service API.
          params: (:py:class:`dict`, optional): The values for format
            into the created URL (defaults to ``None``).
          url_params: (:py:class:`dict`, optional): Parameters to add
            to the end of the URL (defaults to ``None``).

        Returns:
          :py:class:`str`: The resulting URL.

        """
        if root is None:
            root = self.ROOT
        return ''.join([
            root,
            endpoint,
            '?' + urlencode(url_params) if url_params else '',
        ]).format(**params or {})

    @classmethod
    def from_config(cls, **config):
        """Manipulate the configuration settings."""
        missing = cls.REQUIRED.difference(config)
        if missing:
            message = 'missing required config keys ({}) from {}'
            raise TypeError(message.format(
                ', '.join(missing),
                unescape(cls.FRIENDLY_NAME),
            ))
        instance = cls(**config)
        return instance

    @staticmethod
    def calculate_timeout(http_date):
        """Extract request timeout from e.g. ``Retry-After`` header.

        Notes:
          Per :rfc:`2616#section-14.37`, the ``Retry-After`` header can
          be either an integer number of seconds or an HTTP date. This
          function can handle either.

        Arguments:
          http_date (:py:class:`str`): The date to parse.

        Returns:
          :py:class:`int`: The timeout, in seconds.

        """
        try:
            return int(http_date)
        except ValueError:
            date_after = parse(http_date)
        utc_now = datetime.now(tz=timezone.utc)
        return int((date_after - utc_now).total_seconds())


class ContinuousIntegrationService(Service):
    """Service subclass for common CI behaviour."""

    OUTCOMES = dict()
    """:py:class:`dict`: Mapping from service to Flash outcomes."""

    TEMPLATE = 'ci-section'

    @classmethod
    @abstractmethod
    def format_build(cls, build):
        outcome = build.get('outcome')
        if outcome not in cls.OUTCOMES:
            logger.warning('unknown outcome: %s', outcome)
        return dict(
            author=build.get('author', escape('<no author>')),
            duration=build.get('duration'),
            elapsed=build.get('elapsed'),
            message=build.get('message', escape('<no message>')),
            outcome=cls.OUTCOMES.get(outcome),
            started_at=build.get('started_at'),
        )


class VersionControlService(Service):
    """Service subclass for common (D)VCS behaviour."""

    TEMPLATE = 'vcs-section'

    @classmethod
    @abstractmethod
    def format_commit(cls, commit):
        return dict(
            author=commit.get('author', escape('<no author>')),
            committed=commit.get('committed'),
            message=remove_tags(commit.get('message', '')),
        )


class CustomRootMixin:
    """Mix-in class for implementing custom service roots."""

    REQUIRED = {'root'}
    ROOT = ''

    def __init__(self, *, root, **kwargs):
        super().__init__(**kwargs)
        self.root = root

    def url_builder(self, endpoint, *, root=None, params=None, url_params=None):
        if root is None:
            root = self.root
        return super().url_builder(endpoint=endpoint, root=root, params=params,
                                   url_params=url_params)


class ThresholdMixin:
    """Mix-in class for defining health thresholds.

    Attributes:
      NEUTRAL_THRESHOLD: The threshold beyond which the service is
        considered to be in an error state.
      OK_THRESHOLD: The threshold beyond which the service is
        considered to be in a neutral state.

    """

    NEUTRAL_THRESHOLD = None
    OK_THRESHOLD = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ok_threshold = int(kwargs.get('ok_threshold', self.OK_THRESHOLD))
        self.neutral_threshold = int(kwargs.get(
            'neutral_threshold',
            self.NEUTRAL_THRESHOLD
        ))
