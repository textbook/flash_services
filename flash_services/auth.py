"""Mix-in classes for implementing service authentication."""
# pylint: disable=too-few-public-methods

from collections import OrderedDict


class Unauthenticated:
    """No-op mix-in class for unauthenticated services."""


class TokenAuthMixin:
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

    def url_builder(self, endpoint, params=None, url_params=None):
        """Add authentication URL parameter."""
        if url_params is None:
            url_params = OrderedDict()
        url_params[self.AUTH_PARAM] = self.api_token
        return super().url_builder(
            endpoint,
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
        return {self.AUTH_HEADER: self.api_token}
