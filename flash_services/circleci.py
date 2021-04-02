from .auth import HeaderMixin
from .core import ContinuousIntegrationService


class CircleCI(HeaderMixin, ContinuousIntegrationService):

    AUTH_HEADER = 'Circle-Token'
    ENDPOINT = '/project/{vcs_type}/{username}/{project}/tree/{branch}'
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
        pass

    def format_data(self, data):
        return dict(name=self._name, builds=[], health='neutral')
