"""The services that can be shown on a Flash dashboard."""

from collections import OrderedDict
import logging
from uuid import uuid4

from flask import Blueprint

from .codeship import Codeship
from .github import GitHub
from .tracker import Tracker
from .travis import TravisOS

__author__ = 'Jonathan Sharpe'
__version__ = '0.2.3'

blueprint = Blueprint(
    'services',
    __name__,
    static_folder='static',
    template_folder='templates',
)

logger = logging.getLogger(__name__)

SERVICES = {
    'codeship': Codeship,
    'github': GitHub,
    'tracker': Tracker,
    'travis': TravisOS,
}
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
