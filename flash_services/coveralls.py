"""Defines the GitHub service integration."""

import logging

from .auth import Unauthenticated
from .core import Service, ThresholdMixin
from .utils import occurred, remove_tags

logger = logging.getLogger(__name__)


class Coveralls(Unauthenticated, ThresholdMixin, Service):
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

    ENDPOINT = '/{repo_name}.json'
    FRIENDLY_NAME = 'Coveralls'
    NEUTRAL_THRESHOLD = 50
    OK_THRESHOLD = 80
    ROOT = 'https://coveralls.io'
    TEMPLATE = 'coveralls-section'

    def __init__(self, *, vcs_name, account, repo, **kwargs):
        super().__init__(**kwargs)
        self.repo_name = '/'.join([vcs_name, account, repo])

    @property
    def url_params(self):
        params = super().url_params
        params['page'] = 1
        return params

    def format_data(self, data):
        """Re-format the response data for the front-end.

        Arguments:
          data (:py:class:`dict`): The JSON data from the response.

        Returns:
          :py:class:`dict`: The re-formatted data.

        """
        builds = [self.format_build(build) for build in data.get('builds', [])]

        return dict(
            builds=builds[:4],
            health=self.health(builds[0] if builds else None),
            name=self.repo_name,
        )

    def health(self, last_build):
        """Determine the health of the last build.

        Arguments:
          last_build (:py:class:`dict`): The last build.

        Returns:
          :py:class:`str`: The health rating.

        """
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
            author=build.get('committer_name') or '<no author>',
            committed=occurred(build.get('created_at')),
            coverage=None if coverage is None else '{:.1f}%'.format(coverage),
            message_text=remove_tags(message) if message else None,
            raw_coverage=coverage,
        )
