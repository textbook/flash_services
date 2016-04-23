"""Defines the Travis CI service integrations."""

import logging

import requests

from .core import ContinuousIntegrationService
from .utils import elapsed_time, estimate_time, health_summary

logger = logging.getLogger(__name__)


class TravisOS(ContinuousIntegrationService):
    """Show the current status of an open-source project.

    Arguments:
      account (:py:class:`str`): The name of the account.
      app (:py:class:`str`): The name of the application.

    Attributes:
      repo (:py:class:`str`): The repository name, in the format
        ``account/application``.

    """

    FRIENDLY_NAME = 'Travis CI'
    OUTCOMES = {
        'canceled': 'cancelled',
        'created': 'working',
        'failed': 'failed',
        'passed': 'passed',
        'started': 'working',
        '?': 'crashed',
    }
    REQUIRED = {'account', 'app'}
    ROOT = 'https://api.travis-ci.org'

    def __init__(self, *, account, app, **kwargs):
        super().__init__(**kwargs)
        self.account = account
        self.app = app
        self.repo = '{}/{}'.format(account, app)

    @property
    def headers(self):
        headers = super().headers
        headers.update({
            'Accept': 'application/vnd.travis-ci.2+json',
            'User-Agent': 'Flash',
        })
        return headers

    def update(self):
        logger.debug('fetching Travis CI project data')
        response = requests.get(
            self.url_builder(
                '/repos/{repo}/builds',
                params={'repo': self.repo},
            ),
            headers=self.headers,
        )
        if response.status_code == 200:
            return self.format_data(response.json())
        logger.error('failed to update Travis CI project data')
        return {}

    def format_data(self, data):
        """Re-format the response data for the front-end.

        Arguments:
          data (:py:class:`dict`): The JSON data from the response.

        Returns:
          :py:class:`dict`: The re-formatted data.

        """
        commits = {commit['id']: commit for commit in data.get('commits', [])}
        builds = [
            self.format_build(build, commits.get(build.get('commit_id'), {}))
            for build in data.get('builds', [])
        ]
        estimate_time(builds)
        return dict(
            builds=builds[:4],
            health=health_summary(builds),
            name=self.repo,
        )

    @classmethod
    def format_build(cls, build, commit):  # pylint: disable=arguments-differ
        """Re-format the build and commit data for the front-end.

        Arguments:
          build (:py:class:`dict`): The build data from the response.
          commit (:py:class:`dict`): The commit data from the response.

        Returns:
          :py:class:`dict`: The re-formatted data.

        """
        start, finish, elapsed = elapsed_time(
            build.get('started_at'),
            build.get('finished_at'),
        )
        return super().format_build(dict(
            author=commit.get('author_name'),
            duration=(
                None if start is None or finish is None else finish - start
            ),
            elapsed=elapsed,
            message=commit.get('message'),
            outcome=build.get('state'),
            started_at=start,
        ))
