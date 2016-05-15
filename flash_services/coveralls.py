"""Defines the GitHub service integration."""

import logging
from collections import OrderedDict

import requests

from .auth import Unauthenticated
from .core import Service
from .utils import occurred, remove_tags

logger = logging.getLogger(__name__)


class Coveralls(Unauthenticated, Service):
    """Show the current status of a Coveralls repository.

    Arguments:
      vcs_name (:py:class:`str`): The name of the linked VCS (e.g.
        ``'github'``).
      account (:py:class:`str`): The name of the account.
      repo (:py:class:`str`): The name of the repository.
      ok_threshold (:py:class:`int`, optional): The minimum coverage
        for OK tile status (defaults to ``80``).
      neutral_threshold (:py:class:`int`, optional): The minimum
        coverage for neutral tile status (defaults to ``50``).

    Attributes:
      repo_name (:py:class:`str`): The repository name, in the format
        ``vcs_name/account/repo``.

    """

    FRIENDLY_NAME = 'Coveralls'
    REQUIRED = {'vcs_name', 'account', 'repo'}
    ROOT = 'https://coveralls.io'
    TEMPLATE = 'coveralls-section'

    def __init__(self, *, vcs_name, account, repo, **kwargs):
        super().__init__(**kwargs)
        self.account = account
        self.repo = repo
        self.vcs_name = vcs_name
        self.ok_threshold = kwargs.get('ok_threshold', 80)
        self.neutral_threshold = kwargs.get('neutral_threshold', 50)

    @property
    def repo_name(self):
        return '/'.join([self.vcs_name, self.account, self.repo])

    def update(self):
        logger.debug('fetching Coveralls project data')
        response = requests.get(
            self.url_builder(
                '/{repo}.json',
                params={'repo': self.repo_name},
                url_params=OrderedDict(page=1),
            ),
            headers=self.headers,
        )
        if response.status_code == 200:
            return self.format_data(self.repo_name, response.json())
        logger.error('failed to update Coveralls project data')
        return {}

    def format_data(self, name, data):
        """Re-format the response data for the front-end.

        Arguments:
          data (:py:class:`dict`): The JSON data from the response.
          name (:py:class:`str`): The name of the repository.

        Returns:
          :py:class:`dict`: The re-formatted data.

        """
        builds = [self.format_build(build) for build in data.get('builds', [])]

        return dict(
            builds=builds[:4],
            health=self.health(builds[0] if builds else None),
            name=name,
        )

    def health(self, last_build):
        if last_build is None:
            return 'error'
        coverage = last_build['raw_coverage']
        if coverage is None or coverage < self.neutral_threshold:
            return 'error'
        elif coverage < self.ok_threshold:
            return 'neutral'
        return 'ok'

    @classmethod
    def format_build(cls, build):
        """Re-format the build data for the front-end.

        Arguments:
          build (:py:class:`dict`): The JSON data from the response.

        Returns:
          :py:class:`dict`: The re-formatted data.

        """
        coverage = build.get('covered_percent')
        message = build.get('commit_message')
        return dict(
            author=build.get('committer_name', '&lt;no author&gt;'),
            committed=occurred(build.get('created_at')),
            coverage=None if coverage is None else '{:.1f}%'.format(coverage),
            message_text=remove_tags(message) if message else None,
            raw_coverage=coverage,
        )
