"""Core service description."""

from abc import ABCMeta, abstractmethod
import logging
from datetime import datetime
from datetime import timezone
from urllib.parse import urlencode

from dateutil.parser import parse

logger = logging.getLogger(__name__)


class Service(metaclass=ABCMeta):
    """Abstract base class for services."""

    FRIENDLY_NAME = '<unnamed>'
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
            raise TypeError('missing required config keys: {!s}'.format(
                ', '.join(missing)
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
            author=build.get('author', '&lt;no author&gt;'),
            duration=build.get('duration'),
            elapsed=build.get('elapsed'),
            message=build.get('message', '&lt;no message&gt;'),
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
            author=commit.get('author', '&lt;no author&gt;'),
            committed=commit.get('committed'),
            message=commit.get('message', ''),
        )
