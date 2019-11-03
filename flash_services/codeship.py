"""Defines the Codeship CI service integration."""
import logging

from .auth import UrlParamMixin
from .core import ContinuousIntegrationService
from .utils import elapsed_time, estimate_time, health_summary, Outcome

logger = logging.getLogger(__name__)


class Codeship(UrlParamMixin, ContinuousIntegrationService):
    """Show the current build status on Codeship.

    Arguments:
      api_token (:py:class:`str`): A valid token for the Codeship API.
      project_id (:py:class:`int`): The ID of the Codeship project.

    """

    AUTH_PARAM = 'api_key'
    ENDPOINT = '/projects/{project_id}.json'
    FRIENDLY_NAME = 'Codeship CI'
    OUTCOMES = dict(
        cancelled=Outcome.CANCELLED,
        error=Outcome.FAILED,
        infrastructure_failure=Outcome.CRASHED,
        stopped=Outcome.CANCELLED,
        success=Outcome.PASSED,
        testing=Outcome.WORKING,
    )
    ROOT = 'https://codeship.com/api/v1'

    def __init__(self, *, project_id, **kwargs):
        super().__init__(**kwargs)
        self.project_id = project_id

    @classmethod
    def format_data(cls, data):
        """Re-format the response data for the front-end.

        Arguments:
          data (:py:class:`dict`): The JSON data from the response.

        Returns:
          :py:class:`dict`: The re-formatted data.

        """
        builds = [cls.format_build(build) for build in data.get('builds', [])]
        estimate_time(builds)
        return dict(
            builds=builds[:4],
            health=health_summary(builds),
            name=data.get('repository_name'),
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
            build.get('started_at'),
            build.get('finished_at'),
        )
        return super().format_build(dict(
            author=build.get('github_username'),
            duration=(
                None if start is None or finish is None else finish - start
            ),
            elapsed=elapsed,
            message=build.get('message'),
            outcome=build.get('status'),
            started_at=start,
        ))
