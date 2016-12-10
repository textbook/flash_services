"""Defines the Jenkins CI service integration."""

import logging
import time

import requests

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

    OUTCOMES = {
        None: 'working',
        'FAILURE': 'failed',
        'UNSTABLE': 'failed',
        'SUCCESS': 'passed',
    }

    REQUIRED = {'job'}.union(
        BasicAuthHeaderMixin.REQUIRED,
        ContinuousIntegrationService.REQUIRED,
        CustomRootMixin.REQUIRED,
    )


    TREE_PARAMS = 'name,builds[timestamp,duration,result,description,changeSets[items[author[fullName],comment]]]'  # pylint: disable=line-too-long
    """:py:class:`str`: Definition of JSON tree to return."""

    def __init__(self, *, job, **kwargs):
        super().__init__(**kwargs)
        self.job = job

    def update(self):
        logger.debug('fetching Jenkins project data')
        response = requests.get(
            self.url_builder(
                '/job/{job}/api/json',
                params={'job': self.job},
                url_params={'tree': self.TREE_PARAMS}
            ),
            headers=self.headers
        )
        if response.status_code != 200:
            logger.error('failed to update Jenkins project data')
            return {}
        return self.format_data(response.json())

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
            builds=builds,
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
        items = changes[0].get('items')
        if not items:
            return None, None
        item = items[0]
        return item.get('author', {}).get('fullName'), item.get('comment')
