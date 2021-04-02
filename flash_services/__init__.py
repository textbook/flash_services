"""The services that can be shown on a Flash dashboard."""

from collections import OrderedDict
import logging
from uuid import uuid4

from flask import Blueprint

from .buddy import Buddy
from .circleci import CircleCI
from .codeship import Codeship
from .coveralls import Coveralls
from .github import (GitHub, GitHubEnterprise, GitHubEnterpriseIssues,
                     GitHubIssues)
from .jenkins import Jenkins
from .tracker import Tracker
from .travis import TravisOS, TravisPro

__author__ = 'Jonathan Sharpe'
__version__ = '0.11.0'

blueprint = Blueprint(
    'services',
    __name__,
    static_folder='static',
    template_folder='templates',
)

logger = logging.getLogger(__name__)

# pylint: disable=fixme
# TODO: add services here and in static/scripts/services.js
SERVICES = dict(
    buddy=Buddy,
    circleci=CircleCI,
    codeship=Codeship,
    coveralls=Coveralls,
    github=GitHub,
    github_enterprise=GitHubEnterprise,
    gh_issues=GitHubIssues,
    ghe_issues=GitHubEnterpriseIssues,
    jenkins=Jenkins,
    tracker=Tracker,
    travis=TravisOS,
    travis_pro=TravisPro,
)
""":py:class:`dict`: The services available to the application."""


def define_services(config):
    """Define the service settings for the current app.

    Arguments:
      config (:py:class:`list`): The service configuration required.

    Returns:
      :py:class:`collections.OrderedDict`: Configured services.

    Raises:
      :py:class:`ValueError`: If a non-existent service is requested.

    """
    services = OrderedDict()
    for settings in config:
        name = settings['name']
        if name not in SERVICES:
            logger.warning('unknown service %r', name)
            continue
        services[uuid4().hex] = SERVICES[name].from_config(**settings)
    return services
