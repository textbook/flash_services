from .auth import HeaderMixin
from .core import ContinuousIntegrationService
from .utils import elapsed_time, estimate_time, health_summary, Outcome


class CircleCI(HeaderMixin, ContinuousIntegrationService):
    """Show the current build status on Circle CI.

    Arguments:
      api_token (:py:class:`str`): A valid token for the Circle CI API.
      branch (:py:class:`str`): The name of the branch.
      project (:py:class:`str`): The name of the project/repo.
      username (:py:class:`str`): The name of the user/org.
      vcs_type (:py:class:`str`): Which version control system type the
        project uses.

    """

    AUTH_HEADER = 'Circle-Token'
    ENDPOINT = '/project/{vcs_type}/{username}/{project}/tree/{branch}'
    OUTCOMES = dict(
        retried=Outcome.CANCELLED,
        canceled=Outcome.CANCELLED,
        infrastructure_fail=Outcome.CRASHED,
        timedout=Outcome.CRASHED,
        not_run=Outcome.CANCELLED,
        running=Outcome.WORKING,
        failed=Outcome.FAILED,
        queued=Outcome.WORKING,
        scheduled=Outcome.WORKING,
        not_running=Outcome.WORKING,
        no_tests=Outcome.CRASHED,
        fixed=Outcome.PASSED,
        success=Outcome.PASSED
    )
    ROOT = 'https://circleci.com/api/v1.1'

    def __init__(self, *, vcs_type, username, project, branch, **kwargs):
        self.vcs_type = vcs_type
        self.username = username
        self.project = project
        self.branch = branch
        self._name = "{0.vcs_type}/{0.username}/{0.project} [{0.branch}]".format(self)
        super().__init__(**kwargs)

    @property
    def headers(self):
        headers = super().headers
        headers.update(dict(Accept='application/json'))
        return headers

    @property
    def url_params(self):
        params = super().url_params
        params.update(dict(limit=100, shallow='true'))
        return params

    @classmethod
    def format_build(cls, build):
        start, finish, elapsed = elapsed_time(
            build.get('start_time'),
            build.get('stop_time'),
        )
        duration = None if start is None or finish is None else finish - start
        return super().format_build(dict(
            author=build.get('committer_name'),
            duration=duration,
            elapsed=elapsed,
            message=build.get('subject'),
            outcome=build.get('status'),
            started_at=start,
        ))

    def format_data(self, data):
        builds = [self.format_build(build) for build in data]
        estimate_time(builds)
        return dict(name=self._name, builds=builds[:4], health=health_summary(builds))
