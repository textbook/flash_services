"""Mix-in classes for implementing service authentication."""
# pylint: disable=too-few-public-methods

from base64 import b64encode
from collections import OrderedDict

from .core import MixinMeta


class AuthMixin(metaclass=MixinMeta):
    """Root class for all authentication mix-ins."""


class Unauthenticated(AuthMixin):
    """No-op mix-in class for unauthenticated services."""


class TokenAuthMixin(AuthMixin):
    """Mix-in class for implementing token authentication."""

    TOKEN_ENV_VAR = None
    """:py:class:`str`: The environment variable holding the token."""

    def __init__(self, *, api_token, **kwargs):
        self.api_token = api_token
        super().__init__(**kwargs)


class UrlParamMixin(TokenAuthMixin):
    """Mix-in class for implementing URL parameter authentication."""

    AUTH_PARAM = None
    """:py:class:`str`: The name of the URL parameter."""

    def url_builder(self, endpoint, *, root=None, params=None, url_params=None):
        """Add authentication URL parameter."""
        if url_params is None:
            url_params = OrderedDict()
        url_params[self.AUTH_PARAM] = self.api_token
        return super().url_builder(
            endpoint,
            root=root,
            params=params,
            url_params=url_params,
        )


class HeaderMixin(TokenAuthMixin):
    """Mix-in class for implementing header authentication."""

    AUTH_HEADER = None
    """:py:class:`str`: The name of the request header."""

    @property
    def headers(self):
        """Add authentication header."""
        headers = super().headers
        headers.update({self.AUTH_HEADER: self.api_token})
        return headers


class BasicAuthHeaderMixin(AuthMixin):
    """Mix-in class for HTTP Basic auth."""

    def __init__(self, *, username, password, **kwargs):
        self.username = username
        self.password = password
        super().__init__(**kwargs)

    @property
    def headers(self):
        """Get the headers for the service requests."""
        encoding = 'utf8'
        headers = super().headers
        token = b64encode(bytes('{}:{}'.format(
            self.username,
            self.password
        ), encoding))
        headers['Authorization'] = 'Basic {}'.format(str(token, encoding))
        return headers
