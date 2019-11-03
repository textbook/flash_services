"""Defines the Jenkins CI service integration."""

import logging
import time

from .auth import BasicAuthHeaderMixin
from .core import ContinuousIntegrationService, CustomRootMixin
from .utils import estimate_time, health_summary, naturaldelta

logger = logging.getLogger(__name__)


class Jenkins(BasicAuthHeaderMixin, CustomRootMixin,
              ContinuousIntegrationService):
    """Show the current build status on a Jenkins instance.

    Arguments:
      username (:py:class:`str`): A valid username for the Jenkins
        instance.
      password (:py:class:`str`): A valid password for the Jenkins
        instance.
      root (:py:class:`str`): The root URL for the Jenkins instance.
      job (:py:class:`str`): The name of the job (must match the job
        URL).

    """

    ENDPOINT = '/job/{job}/api/json'

    OUTCOMES = {
        None: 'working',
        'WORKING': 'working',
        'FAILURE': 'failed',
        'UNSTABLE': 'failed',
        'SUCCESS': 'passed',
        'ABORTED': 'cancelled',
    }

    TREE_PARAMS = 'name,builds[building,timestamp,duration,result,description,changeSets[items[author[fullName],comment]]]'  # pylint: disable=line-too-long
    """:py:class:`str`: Definition of JSON tree to return."""

    def __init__(self, *, job, **kwargs):
        super().__init__(**kwargs)
        self.job = job

    @property
    def url_params(self):
        params = super().url_params
        params['tree'] = self.TREE_PARAMS
        return params

    @classmethod
    def format_data(cls, data):
        """Re-format the response data for the front-end.

        Arguments:
          data (:py:class:`dict`): The JSON data from the response.

        Returns:
          :py:class:`dict`: The re-formatted data.

        """
        builds = [cls.format_build(build) for build in data['builds']]
        estimate_time(builds)
        return dict(
            builds=builds[:4],
            health=health_summary(builds),
            name=data['name'],
        )

    @classmethod
    def format_build(cls, build):
        """Re-format the build data for the front-end.

        Arguments:
          build (:py:class:`dict`): The JSON data from the response.

        Returns:
          :py:class:`dict`: The re-formatted data.

        Note:
          Jenkins returns timestamps in milliseconds, and always has a
          zero ``duration`` for the in-progress build.

        """
        started_at = build['timestamp'] // 1000
        duration = (build['duration'] // 1000) or None
        if build.get('building'):
            build['result'] = 'WORKING'
        if duration is not None:
            elapsed = 'took {}'.format(naturaldelta(duration))
        else:
            duration = int(time.time()) - started_at
            elapsed = 'elapsed time not available'
        author, message = cls._extract_change(build)
        return super().format_build(dict(
            author=author,
            duration=duration,
            elapsed=elapsed,
            message=message,
            outcome=build['result'],
            started_at=started_at,
        ))

    @classmethod
    def _extract_change(cls, build):
        """Extract the most recent change-set items from the build.

        Arguments:
          build (:py:class:`dict`): The JSON data from the response.

        Returns:
          :py:class:`tuple`: The author and message.

        """
        changes = build.get('changeSets')
        if not changes:
            return None, None
        items = changes[-1].get('items')
        if not items:
            return None, None
        item = items[0]
        return item.get('author', {}).get('fullName'), item.get('comment')
