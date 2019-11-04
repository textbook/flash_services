"""Core service description."""

from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from datetime import datetime
from datetime import timezone
import logging
from urllib.parse import urlencode

import requests
from dateutil.parser import parse

from .utils import provided_args, remove_tags, required_args

logger = logging.getLogger(__name__)


class MixinMeta(type):
    """Metaclass for all mix-ins."""

    def __new__(mcs, name, bases, attrs):
        """Update the new class with appropriate attributes.

        Arguments:
          mcs (:py:class:`type`): The newly-created class.
          name (:py:class:`str`): The name of the class.
          bases (:py:class:`tuple`): The base classes of the class.
          attrs (:py:class:`dict`): The attributes of the class.

        Returns:
          :py:class:`type`: The class, updated.

        Note:
          The ``REQUIRED`` configuration of each class is the union of
          the required configuration keys of all of its base classes,
          excluding the ``PROVIDED`` configuration keys.

        """
        all_provided = provided_args(attrs)
        attrs['PROVIDED'] = all_provided
        base_required = [required_args(base.__dict__) for base in bases]
        all_required = set.union(required_args(attrs), *base_required)
        attrs['REQUIRED'] = set.difference(all_required, all_provided)
        return super().__new__(mcs, name, bases, attrs)


class ServiceMeta(ABCMeta, MixinMeta):
    """Metaclass to simplify configuration."""

    def __new__(mcs, name, bases, attrs):  # pylint: disable=arguments-differ
        """Update the new class with appropriate attributes.

        Arguments:
          mcs (:py:class:`type`): The newly-created class.
          name (:py:class:`str`): The name of the class.
          bases (:py:class:`tuple`): The base classes of the class.
          attrs (:py:class:`dict`): The attributes of the class.

        Returns:
          :py:class:`type`: The class, updated.

        Note:
          The ``FRIENDLY_NAME`` defaults to ``name`` if not explicitly
          provided.

        """
        attrs['FRIENDLY_NAME'] = attrs.get('FRIENDLY_NAME', name)
        return super().__new__(mcs, name, bases, attrs)


class Service(metaclass=ServiceMeta):
    """Abstract base class for services."""

    ENDPOINT = None
    """:py:class:`str`: The endpoint URL template for the service API."""

    FRIENDLY_NAME = None
    """:py:class:`str`: The friendly name of the service."""

    REQUIRED = set()
    """:py:class:`set`: The service's required configuration keys."""

    ROOT = None
    """:py:class:`str`: The root URL for the service API."""

    TEMPLATE = 'undefined-section'
    """:py:class:`str`: The name of the template to render."""

    @abstractmethod
    def __init__(self, **kwargs):
        self.service_name = kwargs.get('name')

    def update(self):
        """Get the current state to display on the dashboard."""
        logger.debug('fetching %s project data', self.FRIENDLY_NAME)
        response = requests.get(self.url, headers=self.headers)
        if response.status_code == 200:
            return self.format_data(response.json())
        logger.error('failed to update %s project data', self.FRIENDLY_NAME)
        return {}

    @abstractmethod
    def format_data(self, data):
        """Re-format the response data for the front-end.

        Arguments:
          data (:py:class:`dict`): The JSON data from the response.

        Returns:
          :py:class:`dict`: The re-formatted data.

        """
        raise NotImplementedError

    @property
    def url(self):
        """Generate the URL for the service request."""
        return self.url_builder(
            self.ENDPOINT,
            root=getattr(self, 'root', self.ROOT),
            params=self.__dict__,
            url_params=self.url_params,
        )

    @property
    def headers(self):
        """Get the headers for the service requests."""
        return {}

    @property
    def url_params(self):
        return OrderedDict()

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
                cls.FRIENDLY_NAME or cls.__name__,
            ))
        instance = cls(**config)
        return instance

    @staticmethod
    def calculate_timeout(http_date):
        """Extract request timeout from e.g. ``Retry-After`` header.

        Note:
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
        """Re-format the build data for the front-end.

        Arguments:
          build (:py:class:`dict`): The JSON data from the response.

        Returns:
          :py:class:`dict`: The re-formatted data.

        """
        outcome = build.get('outcome')
        if outcome not in cls.OUTCOMES:
            logger.warning('unknown outcome: %s', outcome)
        return dict(
            author=build.get('author') or '<no author>',
            duration=build.get('duration'),
            elapsed=build.get('elapsed'),
            message=build.get('message') or '<no message>',
            outcome=cls.OUTCOMES.get(outcome),
            started_at=build.get('started_at'),
        )


class VersionControlService(Service):
    """Service subclass for common (D)VCS behaviour."""

    TEMPLATE = 'vcs-section'

    @classmethod
    @abstractmethod
    def format_commit(cls, commit):
        """Format the raw commit from the service.

        Arguments:
          commit (:py:class:`dict`): The raw commit from the service.

        Returns:
          :py:class:`dict`): The formatted commit.

        """
        return dict(
            author=commit.get('author') or '<no author>',
            committed=commit.get('committed'),
            message=remove_tags(commit.get('message') or ''),
        )


class CustomRootMixin(metaclass=MixinMeta):
    """Mix-in class for implementing custom service roots."""

    ROOT = ''

    def __init__(self, *, root, **kwargs):
        super().__init__(**kwargs)
        self.root = root

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
            root = self.root
        return super().url_builder(endpoint=endpoint, root=root, params=params,
                                   url_params=url_params)


class ThresholdMixin(metaclass=MixinMeta):
    """Mix-in class for defining health thresholds.

    Attributes:
      NEUTRAL_THRESHOLD: The threshold beyond which the service is
        considered to be in an error state.
      OK_THRESHOLD: The threshold beyond which the service is
        considered to be in a neutral state.

    """

    NEUTRAL_THRESHOLD = None
    OK_THRESHOLD = None

    def __init__(self, *, ok_threshold=None, neutral_threshold=None, **kwargs):
        super().__init__(**kwargs)
        if ok_threshold is None:
            ok_threshold = self.OK_THRESHOLD
        if neutral_threshold is None:
            neutral_threshold = self.NEUTRAL_THRESHOLD
        self.ok_threshold = ok_threshold
        self.neutral_threshold = neutral_threshold
