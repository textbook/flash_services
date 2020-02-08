"""Defines the GitHub service integration."""

import logging
from collections import defaultdict
from datetime import timedelta

from .auth import BasicAuthHeaderMixin
from .core import CustomRootMixin, ThresholdMixin, VersionControlService
from .utils import naturaldelta, occurred, safe_parse

logger = logging.getLogger(__name__)


class GitHub(BasicAuthHeaderMixin, VersionControlService):
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

    ENDPOINT = '/repos/{repo_name}/commits'
    ROOT = 'https://api.github.com'

    def __init__(self, *, account, repo, branch=None, **kwargs):
        super().__init__(**kwargs)
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

    @property
    def url_params(self):
        params = super().url_params
        if self.branch:
            params['sha'] = self.branch
        return params

    def format_data(self, data):
        """Re-format the response data for the front-end.

        Arguments:
          data (:py:class:`list`): The JSON data from the response.

        Returns:
          :py:class:`dict`: The re-formatted data.

        """
        return dict(
            commits=[
                self.format_commit(commit.get('commit', {}))
                for commit in data[:5] or []
            ],
            name=self.name,
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

    ENDPOINT = '/repos/{repo_name}/issues'
    FRIENDLY_NAME = 'GitHub Issues'
    NEUTRAL_THRESHOLD = 30
    OK_THRESHOLD = 7
    TEMPLATE = 'gh-issues-section'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.branch = None  # branches aren't relevant for issues

    @property
    def url_params(self):
        params = super().url_params
        params['state'] = 'all'
        return params

    def format_data(self, data):
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
            name=self.name,
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

    FRIENDLY_NAME = 'GitHub'


class GitHubEnterpriseIssues(CustomRootMixin, GitHubIssues):
    """Issues and pull requests from GHE repositories."""

    FRIENDLY_NAME = 'GitHub Issues'
