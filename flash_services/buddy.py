"""Defines the Buddy CI service integration."""
import logging

from .auth import BearerAuthHeaderMixin
from .core import ContinuousIntegrationService
from .utils import elapsed_time, estimate_time, health_summary, Outcome

logger = logging.getLogger(__name__)


class Buddy(BearerAuthHeaderMixin, ContinuousIntegrationService):
    """Show the current build status on Buddy.

    Arguments:
      api_token (:py:class:`str`): A valid token for the Buddy API.
      domain (:py:class:`str`): The domain of the Buddy project.
      pipeline_id (:py:class:`int`): The ID of the Buddy pipeline.
      project_name (:py:class:`str`): The name of the Buddy project.

    """

    ENDPOINT = '/workspaces/{domain}/projects/{project_name}/pipelines/{pipeline_id}/executions'
    OUTCOMES = dict(
        FAILED=Outcome.FAILED,
        INPROGRESS=Outcome.WORKING,
        SUCCESSFUL=Outcome.PASSED,
        TERMINATED=Outcome.CANCELLED,
    )
    ROOT = 'https://api.buddy.works'

    def __init__(self, *, domain, pipeline_id, project_name, **kwargs):
        super().__init__(**kwargs)
        self.domain = domain
        self.pipeline_id = pipeline_id
        self.project_name = project_name

    def format_data(self, data):
        """Re-format the response data for the front-end.

        Arguments:
          data (:py:class:`dict`): The JSON data from the response.

        Returns:
          :py:class:`dict`: The re-formatted data.

        """
        builds = [self.format_build(build) for build in data['executions']]
        estimate_time(builds)
        return dict(
            builds=builds[:4],
            health=health_summary(builds),
            name='{0.domain}/{0.project_name} ({0.pipeline_id})'.format(self),
        )

    @classmethod
    def format_build(cls, build):
        """Re-format the build data for the front-end.

        Arguments:
          build (:py:class:`dict`): The JSON data from the response.

        Returns:
          :py:class:`dict`: The re-formatted data.

        """
        start, finish, elapsed = elapsed_time(
            build.get('start_date'),
            build.get('finish_date'),
        )
        commit = build.get('to_revision', {})
        return super().format_build(dict(
            author=cls.get_name(commit),
            duration=(
                None if start is None or finish is None else finish - start
            ),
            elapsed=elapsed,
            message=cls.get_message(build, commit),
            outcome=build.get('status'),
            started_at=start,
        ))

    @staticmethod
    def get_message(build, commit):
        """Extract the message from the commit or comment.

        Arguments:
          build (:py:class:`dict`): The JSON data from the response.
          commit (:py:class:`dict`): The JSON data from the response.

        Returns:
          :py:class:`str`: The commit or comment message.

        """
        return build.get("comment") or commit.get('message')

    @staticmethod
    def get_name(commit):
        """Extract the name from the author or committer.

        Arguments:
          commit (:py:class:`dict`): The JSON data from the response.

        Returns:
          :py:class:`str`: The author (or committer) name.

        """
        author = commit.get('author', {})
        if 'name' in author:
            return author['name']
        return commit.get('committer', {}).get('name')
