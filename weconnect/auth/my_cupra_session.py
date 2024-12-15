from typing import Dict

import json
import logging
import requests

from oauthlib.common import to_unicode
from oauthlib.oauth2 import InsecureTransportError
from oauthlib.oauth2 import is_secure_transport

from requests.models import CaseInsensitiveDict
from weconnect.auth.openid_session import AccessType

from weconnect.auth.vw_web_session import VWWebSession
from weconnect.errors import AuthentificationError, RetrievalError, TemporaryAuthentificationError


LOG = logging.getLogger("weconnect")


class MyCupraSession(VWWebSession):
    def __init__(self, sessionuser, **kwargs):
        super(MyCupraSession, self).__init__(client_id='3c756d46-f1ba-4d78-9f9a-cff0d5292d51@apps_vw-dilab_com',
                                             refresh_url='https://identity.vwgroup.io/oidc/v1/token',
                                             scope='openid profile nickname birthdate phone',
                                             redirect_uri='cupra://oauth-callback',
                                             state=None,
                                             sessionuser=sessionuser,
                                             **kwargs)

        self.headers = CaseInsensitiveDict({
            'accept': '*/*',
            'content-type': 'application/json',
            'user-agent': 'CUPRAApp%20-%20Store/20220503 CFNetwork/1333.0.4 Darwin/21.5.0',
            'accept-language': 'de-de',
            'accept-encoding': 'gzip, deflate, br'
        })

    def login(self):
        authorizationUrl = self.authorizationUrl(url='https://identity.vwgroup.io/oidc/v1/authorize')
        response = self.doWebAuth(authorizationUrl)
        self.fetchTokens('https://identity.vwgroup.io/oidc/v1/token',
                         authorization_response=response
                         )

    def refresh(self):
        self.refreshTokens(
            'https://identity.vwgroup.io/oidc/v1/token',
        )

    def fetchTokens(
        self,
        token_url,
        authorization_response=None,
        **kwargs
    ):

        self.parseFromFragment(authorization_response)

        if all(key in self.token for key in ('state', 'id_token', 'access_token', 'code')):
            body: Dict[str, str] = {
                'code': self.token['code'],
                'redirect_uri': self.redirect_uri,
                'client_id': self.client_id,
                'client_secret': 'eb8814e641c81a2640ad62eeccec11c98effc9bccd4269ab7af338b50a94b3a2',
                'grant_type': 'authorization_code',
                'state': self.token['state'],
                'id_token': self.token['id_token']
            }

            loginHeadersForm: CaseInsensitiveDict = self.headers
            loginHeadersForm['content-type'] = 'application/x-www-form-urlencoded; charset=utf-8'

            tokenResponse = self.post(token_url, headers=loginHeadersForm, data=body, allow_redirects=False, access_type=AccessType.NONE)
            if tokenResponse.status_code != requests.codes['ok']:
                print(tokenResponse.text)
                raise TemporaryAuthentificationError(f'Token could not be fetched due to temporary MyCupra failure: {tokenResponse.status_code}')
            token = self.parseFromBody(tokenResponse.text)

            return token

    def parseFromBody(self, token_response, state=None):
        try:
            token = json.loads(token_response)
        except json.decoder.JSONDecodeError:
            raise TemporaryAuthentificationError('Token could not be refreshed due to temporary MyCupra failure: json could not be decoded')
        if 'accessToken' in token:
            token['access_token'] = token.pop('accessToken')
        if 'idToken' in token:
            token['id_token'] = token.pop('idToken')
        if 'refreshToken' in token:
            token['refresh_token'] = token.pop('refreshToken')
        fixedTokenresponse = to_unicode(json.dumps(token)).encode("utf-8")
        return super(MyCupraSession, self).parseFromBody(token_response=fixedTokenresponse, state=state)

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

        body: Dict[str, str] = {
            'client_id': self.client_id,
            'client_secret': 'eb8814e641c81a2640ad62eeccec11c98effc9bccd4269ab7af338b50a94b3a2',
            'grant_type': 'refresh_token',
            'refresh_token': self.token['refresh_token']
        }

        headers['content-type'] = 'application/x-www-form-urlencoded; charset=utf-8'

        tokenResponse = self.post(
            token_url,
            data=body,
            auth=auth,
            timeout=timeout,
            headers=headers,
            verify=verify,
            withhold_token=False,
            proxies=proxies,
            access_type=AccessType.NONE
        )
        if tokenResponse.status_code == requests.codes['unauthorized']:
            raise AuthentificationError('Refreshing tokens failed: Server requests new authorization')
        elif tokenResponse.status_code in (requests.codes['internal_server_error'], requests.codes['service_unavailable'], requests.codes['gateway_timeout']):
            raise TemporaryAuthentificationError('Token could not be refreshed due to temporary MyCupra failure: {tokenResponse.status_code}')
        elif tokenResponse.status_code == requests.codes['ok']:
            self.parseFromBody(tokenResponse.text)
            if "refresh_token" not in self.token:
                LOG.debug("No new refresh token given. Re-using old.")
                self.token["refresh_token"] = refresh_token
            return self.token
        else:
            raise RetrievalError(f'Status Code from MyCupra while refreshing tokens was: {tokenResponse.status_code}')

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
        """Intercept all requests and add userId if present."""
        if not is_secure_transport(url):
            raise InsecureTransportError()
        if self.userId is not None:
            headers = headers or {}
            headers['user-id'] = self.userId

        return super(MyCupraSession, self).request(method, url, headers=headers, data=data, withhold_token=withhold_token, access_type=access_type, token=token,
                                                   timeout=timeout, **kwargs)
