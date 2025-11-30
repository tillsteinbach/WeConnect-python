import json
import logging
import requests

from urllib.parse import parse_qsl, urlparse

from oauthlib.common import add_params_to_uri, generate_nonce, to_unicode
from oauthlib.oauth2 import InsecureTransportError
from oauthlib.oauth2 import is_secure_transport

from requests.models import CaseInsensitiveDict
from weconnect.auth.openid_session import AccessType

from weconnect.auth.vw_web_session import VWWebSession
from weconnect.errors import AuthentificationError, RetrievalError, TemporaryAuthentificationError


LOG = logging.getLogger("weconnect")


class WeConnectSession(VWWebSession):
    def __init__(self, sessionuser, **kwargs):
        super(WeConnectSession, self).__init__(client_id='a24fba63-34b3-4d43-b181-942111e6bda8@apps_vw-dilab_com',
                                               refresh_url='https://identity.vwgroup.io/oidc/v1/token',
                                               scope='openid profile badge cars dealers vin',
                                               redirect_uri='weconnect://authenticated',
                                               state=None,
                                               sessionuser=sessionuser,
                                               **kwargs)

        self.headers = CaseInsensitiveDict({
            'accept': '*/*',
            'content-type': 'application/json',
            'content-version': '1',
            'x-newrelic-id': 'VgAEWV9QDRAEXFlRAAYPUA==',
            'user-agent': 'Volkswagen/3.51.1-android/14',
            'accept-language': 'de-de',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'x-android-package-name': 'com.volkswagen.weconnect'
        })

    def request(
        self,
        method,
        url,
        data=None,
        headers=None,
        withhold_token=False,
        access_type=AccessType.ACCESS,
        token=None,
        timeout=None,
        **kwargs
    ):
        """Intercept all requests and add weconnect-trace-id header."""

        import secrets
        traceId = secrets.token_hex(16)
        weConnectTraceId = (traceId[:8] + '-' + traceId[8:12] + '-' + traceId[12:16] + '-' + traceId[16:20] + '-' + traceId[20:]).upper()
        headers = headers or {}
        headers['weconnect-trace-id'] = weConnectTraceId

        return super(WeConnectSession, self).request(
            method, url, headers=headers, data=data, withhold_token=withhold_token, access_type=access_type, token=token, timeout=timeout, **kwargs
        )

    def login(self):
        super(WeConnectSession, self).login()
        authorizationUrl = self.authorizationUrl(url='https://identity.vwgroup.io/oidc/v1/authorize')
        response = self.doWebAuth(authorizationUrl)
        self.fetchTokens('https://emea.bff.cariad.digital/user-login/login/v1',
                         authorization_response=response
                         )

    def refresh(self):
        self.refreshTokens(
            'https://emea.bff.cariad.digital/login/v1/idk/token',
        )

    def authorizationUrl(self, url, state=None, **kwargs):
        if state is not None:
            raise AuthentificationError('Do not provide state')

        params = [(('redirect_uri', self.redirect_uri)),
                  (('nonce', generate_nonce()))]

        authUrl = add_params_to_uri('https://emea.bff.cariad.digital/user-login/v1/authorize', params)

        tryLoginResponse: requests.Response = self.get(authUrl, allow_redirects=False, access_type=AccessType.NONE)
        redirect = tryLoginResponse.headers['Location']
        query = urlparse(redirect).query
        params = dict(parse_qsl(query))
        if 'state' in params:
            self.state = params.get('state')

        return redirect

    def clearTokens(self) -> None:
        """
        Clear all stored tokens to force a fresh login.
        
        This method is useful when the server requests new authorization
        and we need to clear invalid/expired tokens.
        """
        LOG.info("Clearing all stored tokens")
        self.token = None
        LOG.debug("All tokens cleared successfully")

    def fetchTokens(
        self,
        token_url,
        authorization_response=None,
        **kwargs
    ):
        self.parseFromFragment(authorization_response)

        if all(key in self.token for key in ('state', 'id_token', 'access_token', 'code')):
            body: str = json.dumps(
                {
                    'state': self.token['state'],
                    'id_token': self.token['id_token'],
                    'redirect_uri': self.redirect_uri,
                    'region': 'emea',
                    'access_token': self.token['access_token'],
                    'authorizationCode': self.token['code'],
                })

            loginHeadersForm: CaseInsensitiveDict = self.headers
            loginHeadersForm['accept'] = 'application/json'

            tokenResponse = self.post(token_url, headers=loginHeadersForm, data=body, allow_redirects=False, access_type=AccessType.ID)
            if tokenResponse.status_code != requests.codes['ok']:
                raise TemporaryAuthentificationError(f'Token could not be fetched due to temporary WeConnect failure: {tokenResponse.status_code}')
            token = self.parseFromBody(tokenResponse.text)

            # Ensure the token is properly stored in the session
            if token is not None:
                self.token = token  # Explicitly store the token
                LOG.debug(f"Successfully fetched tokens. Access token expires in: {token.get('expires_in', 'unknown')} seconds")
                LOG.debug(f"Refresh token available: {'refresh_token' in token}")
                # Verify critical tokens are present
                if not all(key in token for key in ('access_token', 'id_token', 'refresh_token')):
                    LOG.warning("Some expected tokens are missing from the response")
            else:
                LOG.error("Token parsing returned None")

            return token
        else:
            LOG.error("Authorization response missing required tokens")
            return None

    def parseFromBody(self, token_response, state=None):
        try:
            token = json.loads(token_response)
        except json.decoder.JSONDecodeError:
            raise TemporaryAuthentificationError('Token could not be refreshed due to temporary WeConnect failure: json could not be decoded')
        if 'accessToken' in token:
            token['access_token'] = token.pop('accessToken')
        if 'idToken' in token:
            token['id_token'] = token.pop('idToken')
        if 'refreshToken' in token:
            token['refresh_token'] = token.pop('refreshToken')
        fixedTokenresponse = to_unicode(json.dumps(token)).encode("utf-8")
        parsedToken = super(WeConnectSession, self).parseFromBody(token_response=fixedTokenresponse, state=state)
        # Ensure the token is stored in the session object
        self.token = parsedToken
        return parsedToken

    def refreshTokens(
        self,
        token_url,
        refresh_token=None,
        auth=None,
        timeout=None,
        headers=None,
        verify=True,
        proxies=None,
        **kwargs
    ):
        LOG.info('Refreshing tokens')
        if not token_url:
            raise ValueError("No token endpoint set for auto_refresh.")

        if not is_secure_transport(token_url):
            raise InsecureTransportError()

        refresh_token = refresh_token or self.refreshToken

        if headers is None:
            headers = self.headers

        # First try to get from the current token property, then fall back to stored token
        if refresh_token is None:
            refresh_token = self.refreshToken
            # If still None, try to get from the token dict directly
            if refresh_token is None and self.token is not None:
                refresh_token = self.token.get('refresh_token')

        if not refresh_token:
            raise AuthentificationError('No refresh token available. Please log in again.')

        # Create headers matching the examples format
        tHeaders = {
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Volkswagen/3.51.1-android/14",
            "x-android-package-name": "com.volkswagen.weconnect",
        }

        # Create form data body matching the examples format
        body = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }

        # Request new tokens using POST with form data
        tokenResponse = self.post(
            token_url,
            data=body,
            headers=tHeaders,
            timeout=timeout,
            verify=verify,
            proxies=proxies,
        )
        if tokenResponse.status_code == requests.codes['unauthorized']:
            LOG.error('Token refresh failed with 401 - server requests new authorization. Refresh token may be expired or invalid.')
            raise AuthentificationError('Refreshing tokens failed: Server requests new authorization. Please log in again.')
        elif tokenResponse.status_code in (requests.codes['internal_server_error'], requests.codes['service_unavailable'], requests.codes['gateway_timeout']):
            raise TemporaryAuthentificationError(f'Token could not be refreshed due to temporary WeConnect failure: {tokenResponse.status_code}')
        elif tokenResponse.status_code == requests.codes['ok']:
            newToken = self.parseFromBody(tokenResponse.text)
            if newToken is not None and "refresh_token" not in newToken:
                LOG.debug("No new refresh token given. Re-using old.")
                self.token["refresh_token"] = refresh_token
                # Update the token property as well
                self.token = newToken
            return newToken
        else:
            raise RetrievalError(f'Status Code from WeConnect while refreshing tokens was: {tokenResponse.status_code}')
