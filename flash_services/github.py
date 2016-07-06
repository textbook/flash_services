"""Defines the GitHub service integration."""

from collections import defaultdict, OrderedDict
from datetime import timedelta
import logging

import requests

from .auth import UrlParamMixin
from .core import CustomRootMixin, ThresholdMixin, VersionControlService
from .utils import naturaldelta, occurred, safe_parse


logger = logging.getLogger(__name__)


class GitHub(UrlParamMixin, VersionControlService):
    """Show the current status of a GitHub repository.

    Arguments:
      api_token (:py:class:`str`): A valid token for the GitHub API.
      account (:py:class:`str`): The name of the account.
      repo (:py:class:`str`): The name of the repository.
      branch (:py:class:`str`, optional): The branch to get commit data
        from.

    Attributes:
      repo_name (:py:class:`str`): The repository name, in the format
        ``account/repo``.

    """

    AUTH_PARAM = 'access_token'
    FRIENDLY_NAME = 'GitHub'
    REQUIRED = {'api_token', 'account', 'repo'}
    ROOT = 'https://api.github.com'

    def __init__(self, *, api_token, account, repo, branch=None, **kwargs):
        super().__init__(api_token=api_token, **kwargs)
        self.account = account
        self.repo = repo
        self.branch = branch
        self.repo_name = '{}/{}'.format(account, repo)

    @property
    def name(self):
        """The full name of the repo, including branch if provided."""
        if self.branch:
            return '{} [{}]'.format(self.repo_name, self.branch)
        return self.repo_name

    @property
    def headers(self):
        headers = super().headers
        headers['User-Agent'] = self.repo
        return headers

    def update(self):
        logger.debug('fetching GitHub project data')
        url_prm = OrderedDict(sha=self.branch) if self.branch else OrderedDict()
        response = requests.get(
            self.url_builder(
                '/repos/{repo}/commits',
                params={'repo': self.repo_name},
                url_params=url_prm,
            ),
            headers=self.headers,
        )
        if response.status_code == 200:
            return self.format_data(self.name, response.json())
        logger.error('failed to update GitHub project data')
        return {}

    @classmethod
    def format_data(cls, name, data):
        """Re-format the response data for the front-end.

        Arguments:
          data (:py:class:`list`): The JSON data from the response.
          name (:py:class:`str`): The name of the repository.

        Returns:
          :py:class:`dict`: The re-formatted data.

        """
        return dict(
            commits=[cls.format_commit(commit.get('commit', {}))
                     for commit in data[:5] or []],
            name=name,
        )

    @classmethod
    def format_commit(cls, commit):
        """Re-format the commit data for the front-end.

        Arguments:
          commit (:py:class:`dict`): The JSON data from the response.

        Returns:
          :py:class:`dict`: The re-formatted data.

        """
        author = commit.get('author', {}).get('name')
        committer = commit.get('committer', {}).get('name')
        if author is None:
            author_name = committer
        elif committer is None or author == committer:
            author_name = author
        else:
            author_name = '{} [{}]'.format(author, committer)
        return super().format_commit(dict(
            author=author_name,
            committed=occurred(commit.get('committer', {}).get('date')),
            message=commit.get('message', ''),
        ))


class GitHubIssues(ThresholdMixin, GitHub):
    """Show the current status of GitHub issues and pull requests."""

    FRIENDLY_NAME = 'GitHub Issues'
    NEUTRAL_THRESHOLD = 30
    OK_THRESHOLD = 7
    TEMPLATE = 'gh-issues-section'

    def __init__(self, *, api_token, account, repo, **kwargs):
        super().__init__(account=account, api_token=api_token, repo=repo,
                         **kwargs)
        self.branch = None  # branches aren't relevant for issues

    def update(self):
        logger.debug('fetching GitHub issue data')
        url_params = OrderedDict(state='all')
        response = requests.get(
            self.url_builder(
                '/repos/{repo}/issues',
                params={'repo': self.repo_name},
                url_params=url_params,
            ),
            headers=self.headers,
        )
        if response.status_code == 200:
            return self.format_data(self.name, response.json())
        logger.error('failed to update GitHub issue data')
        return {}

    def format_data(self, name, data):
        counts = defaultdict(int)
        for issue in data:
            if issue.get('pull_request') is not None:
                counts['{}-pull-requests'.format(issue['state'])] += 1
            else:
                counts['{}-issues'.format(issue['state'])] += 1
        half_life = self.half_life(data)
        return dict(
            halflife=naturaldelta(half_life),
            health=self.health_summary(half_life),
            issues=counts,
            name=name,
        )

    @staticmethod
    def half_life(issues):
        """Calculate the half life of the service's issues.

        Args:
          issues (:py:class:`list`): The service's issue data.

        Returns:
          :py:class:`datetime.timedelta`: The half life of the issues.

        """
        lives = []
        for issue in issues:
            start = safe_parse(issue.get('created_at'))
            end = safe_parse(issue.get('closed_at'))
            if start and end:
                lives.append(end - start)
        if lives:
            lives.sort()
            size = len(lives)
            return lives[((size + (size % 2)) // 2) - 1]

    def health_summary(self, half_life):
        """Calculate the health of the service.

        Args:
          half_life (:py:class:`datetime.timedelta`): The half life of
            the service's issues.

        Returns:
          :py:class:`str`: The health of the service, either ``'ok'``,
            ``'neutral'`` or ``'error'``.

        """
        if half_life is None:
            return 'neutral'
        if half_life <= timedelta(days=self.ok_threshold):
            return 'ok'
        elif half_life <= timedelta(days=self.neutral_threshold):
            return 'neutral'
        return 'error'


class GitHubEnterprise(CustomRootMixin, GitHub):
    """Current status of GHE repositories."""

    REQUIRED = GitHub.REQUIRED | CustomRootMixin.REQUIRED


class GitHubEnterpriseIssues(CustomRootMixin, GitHubIssues):
    """Issues and pull requests from GHE repositories."""

    REQUIRED = GitHubIssues.REQUIRED | CustomRootMixin.REQUIRED
