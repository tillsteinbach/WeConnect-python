import logging
import requests

from oauthlib.common import add_params_to_uri
from oauthlib.oauth2 import InsecureTransportError, is_secure_transport

from requests.models import CaseInsensitiveDict

from weconnect.auth.openid_session import AccessType
from weconnect.auth.vw_web_session import VWWebSession
from weconnect.errors import AuthentificationError, RetrievalError, TemporaryAuthentificationError

LOG = logging.getLogger("weconnect")


class WeChargeSession(VWWebSession):
    def __init__(self, sessionuser, **kwargs):
        super(WeChargeSession, self).__init__(client_id='0fa5ae01-ebc0-4901-a2aa-4dd60572ea0e@apps_vw-dilab_com',
                                              refresh_url='https://identity.vwgroup.io/oidc/v1/token',
                                              scope='openid profile address email cars vin',
                                              redirect_uri='wecharge://authenticated',
                                              state=None,
                                              sessionuser=sessionuser,
                                              **kwargs)

        self.headers = CaseInsensitiveDict({
            'accept': '*/*',
            'content-type': 'application/json',
            'content-version': '1',
            'x-newrelic-id': 'VgAEWV9QDRAEXFlRAAYPUA==',
            'user-agent': 'WeConnect/3 CFNetwork/1327.0.4 Darwin/21.2.0',
            'accept-language': 'de-de',
        })

    @property
    def wcAccessToken(self):
        if self._token is not None and 'wc_access_token' in self._token:
            return self._token.get('wc_access_token')
        return None

    def login(self):
        super(WeChargeSession, self).login()
        authorizationUrl = self.authorizationUrl(url='https://identity.vwgroup.io/oidc/v1/authorize')
        response = self.doWebAuth(authorizationUrl)
        self.fetchTokens('https://wecharge.apps.emea.vwapps.io/user-identity/v1/identity/login',
                         authorization_response=response)

    def refresh(self):
        self.refreshTokens(
            'https://wecharge.apps.emea.vwapps.io/user-identity/v1/identity/login',
        )

    def fetchTokens(
        self,
        token_url,
        authorization_response=None,
        **kwargs
    ):
        self.parseFromFragment(authorization_response)

        if all(key in self.token for key in ('state', 'id_token', 'access_token', 'code')):
            loginHeadersForm: CaseInsensitiveDict = self.headers.copy()
            loginHeadersForm['accept'] = 'application/json'
            loginHeadersForm["x-api-key"] = "yabajourasW9N8sm+9F/oP=="

            urlParams = [(('redirect_uri', self.redirect_uri)),
                         (('code', self.token["code"]))]
            token_url = add_params_to_uri(token_url, urlParams)

            tokenResponse = self.get(token_url, headers=loginHeadersForm, allow_redirects=False, access_type=AccessType.ID)
            if tokenResponse.status_code != requests.codes['ok']:
                raise TemporaryAuthentificationError(f'Token could not be fetched due to temporary WeConnect failure: {tokenResponse.status_code}')

            self.parseFromBody(tokenResponse.text)

            return self.token

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

        refresh_token = refresh_token or self.refresh_token
        if refresh_token is None:
            raise ValueError("Missing refresh token.")

        if headers is None:
            headers = self.headers

        urlParams = [(('redirect_uri', self.redirect_uri)),
                     (('refresh_token', refresh_token))]

        token_url = add_params_to_uri(token_url, urlParams)

        refreshHeaders: CaseInsensitiveDict = headers.copy()
        refreshHeaders['accept'] = 'application/json'
        refreshHeaders["x-api-key"] = "yabajourasW9N8sm+9F/oP=="

        tokenResponse = self.get(
            token_url,
            auth=auth,
            timeout=timeout,
            headers=refreshHeaders,
            verify=verify,
            withhold_token=False,
            proxies=proxies,
            access_type=AccessType.REFRESH
        )
        if tokenResponse.status_code == requests.codes['unauthorized']:
            raise AuthentificationError('Refreshing tokens failed: Server requests new authorization')
        elif tokenResponse.status_code in (requests.codes['internal_server_error'], requests.codes['service_unavailable'], requests.codes['gateway_timeout']):
            raise TemporaryAuthentificationError('Token could not be refreshed due to temporary WeConnect failure: {tokenResponse.status_code}')
        elif tokenResponse.status_code == requests.codes['ok']:
            self.parseFromBody(tokenResponse.text)
            if "refresh_token" not in self.token:
                LOG.debug("No new refresh token given. Re-using old.")
                self.token["refresh_token"] = refresh_token
            return self.token
        else:
            raise RetrievalError(f'Status Code from WeConnect while refreshing tokens was: {tokenResponse.status_code}')

    def addToken(self, uri, body=None, headers=None, access_type=AccessType.ACCESS, **kwargs):
        headers = headers or {}
        uri, headers, body = super(WeChargeSession, self).addToken(uri, body=body, headers=headers, access_type=access_type, **kwargs)

        if access_type == AccessType.ACCESS:
            if not (self.wcAccessToken):
                raise ValueError("Missing wc access token.")
            headers['wc_access_token'] = self.wcAccessToken

        return (uri, headers, body)
