from enum import Enum, auto
import time
from oauthlib.oauth2.rfc6749.errors import InsecureTransportError, TokenExpiredError
from oauthlib.oauth2.rfc6749.utils import is_secure_transport

import requests

from oauthlib.common import UNICODE_ASCII_CHARACTER_SET, generate_nonce, generate_token
from oauthlib.oauth2.rfc6749.parameters import parse_authorization_code_response, parse_token_response, prepare_grant_uri

from weconnect.auth.auth_util import addBearerAuthHeader


class AccessType(Enum):
    NONE = auto()
    ACCESS = auto()
    ID = auto()
    REFRESH = auto()


class OpenIDSession(requests.Session):
    def __init__(self, client_id=None, redirect_uri=None, refresh_url=None, scope=None, token=None, state=None, **kwargs):
        super(OpenIDSession, self).__init__(**kwargs)
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.refresh_url = refresh_url
        self.scope = scope
        self.token = token
        self.state = state or generate_token(length=30, chars=UNICODE_ASCII_CHARACTER_SET)

        self.access_token = None
        self.refresh_token = None
        self.id_token = None
        self.token_type = None
        self.expires_in = None
        self.expires_at = None

    def login(self):
        pass

    def authorization_url(self, url, state=None, **kwargs):
        state = state or self.state
        authUrl = prepare_grant_uri(uri=url, client_id=self.client_id, redirect_uri=self.redirect_uri, response_type='code id_token token', scope=self.scope,
                                    state=state, nonce=generate_nonce(), **kwargs)
        return authUrl

    def parseFromFragment(self, authorization_response, state=None):
        state = state or self.state
        code = parse_authorization_code_response(authorization_response, state=state)
        self.safeTokenAttributes(code)
        return code

    def parseFromBody(self, token_response, state=None):
        self.token = parse_token_response(token_response, scope=self.scope)
        self.safeTokenAttributes(self.token)
        return self.token

    def safeTokenAttributes(self, response):
        """Add attributes from a token exchange response to self."""

        if 'access_token' in response:
            self.access_token = response.get('access_token')

        if 'refresh_token' in response:
            self.refresh_token = response.get('refresh_token')

        if 'id_token' in response:
            self.id_token = response.get('id_token')
        
        if 'token_type' in response:
            self.token_type = response.get('token_type')

        if 'expires_in' in response:
            self.expires_in = response.get('expires_in')
            self.expires_at = time.time() + int(self.expires_in)

        if 'expires_at' in response:
            try:
                self._expires_at = int(response.get('expires_at'))
            except ValueError:
                self._expires_at = None

    @property
    def authorized(self):
        """Boolean that indicates whether this session has an OAuth token
        or not. If `self.authorized` is True, you can reasonably expect
        OAuth-protected requests to the resource to succeed. If
        `self.authorized` is False, you need the user to go through the OAuth
        authentication dance before OAuth-protected requests to the resource
        will succeed.
        """
        return bool(self.access_token)

    def request(
        self,
        method,
        url,
        data=None,
        headers=None,
        withhold_token=False,
        access_type=AccessType.ACCESS,
        **kwargs
    ):
        """Intercept all requests and add the OAuth 2 token if present."""
        if not is_secure_transport(url):
            raise InsecureTransportError()
        if access_type != AccessType.NONE and not withhold_token:
            try:
                url, headers, data = self.addToken(url, body=data, headers=headers, access_type=access_type)
            # Attempt to retrieve and save new access token if expired
            except TokenExpiredError:
                pass
            #     if self.auto_refresh_url:
            #         log.debug(
            #             "Auto refresh is set, attempting to refresh at %s.",
            #             self.auto_refresh_url,
            #         )

            #         # We mustn't pass auth twice.
            #         auth = kwargs.pop("auth", None)
            #         if client_id and client_secret and (auth is None):
            #             log.debug(
            #                 'Encoding client_id "%s" with client_secret as Basic auth credentials.',
            #                 client_id,
            #             )
            #             auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
            #         token = self.refresh_token(
            #             self.auto_refresh_url, auth=auth, **kwargs
            #         )
            #         if self.token_updater:
            #             log.debug(
            #                 "Updating token to %s using %s.", token, self.token_updater
            #             )
            #             self.token_updater(token)
            #             url, headers, data = self._client.add_token(
            #                 url, http_method=method, body=data, headers=headers
            #             )
            #         else:
            #             raise TokenUpdated(token)
            #     else:
            #         raise

        return super(OpenIDSession, self).request(
            method, url, headers=headers, data=data, **kwargs
        )

    def addToken(self, uri, body=None, headers=None, access_type=AccessType.ACCESS, **kwargs):
        if not is_secure_transport(uri):
            raise InsecureTransportError()

        if access_type == AccessType.ID:
            if not (self.id_token):
                raise ValueError("Missing id token.")
            token = self.id_token
        elif access_type == AccessType.REFRESH:
            if not (self.refresh_token):
                raise ValueError("Missing refresh token.")
            token = self.refresh_token
        else:
            if not (self.access_token):
                raise ValueError("Missing access token.")
            if self.expires_at and self.expires_at < time.time():
                raise TokenExpiredError()
            token = self.access_token

        headers = addBearerAuthHeader(token, headers)

        return (uri, headers, body)
