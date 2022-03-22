from typing import Dict, Optional, Match

import re
import json
import logging
import requests

from urllib.parse import parse_qsl, urlsplit

from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from oauthlib.common import add_params_to_uri
from oauthlib.oauth2 import InsecureTransportError, is_secure_transport


from requests.models import CaseInsensitiveDict


from weconnect.auth.openid_session import AccessType
from weconnect.auth.vw_web_session import VWWebSession
from weconnect.errors import APICompatibilityError, AuthentificationError, RetrievalError, TemporaryAuthentificationError

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
        authorizationUrl = self.authorizationUrl(url='https://identity.vwgroup.io/oidc/v1/authorize')
        response = self.doWebAuth(authorizationUrl)
        self.fetchTokens('https://wecharge.apps.emea.vwapps.io/user-identity/v1/identity/login',
                         authorization_response=response)

    def refresh(self):
        self.refreshTokens(
            'https://wecharge.apps.emea.vwapps.io/user-identity/v1/identity/login',
        )

    def doWebAuth(self, authorizationUrl):  # noqa: C901
        websession: requests.Session = requests.Session()
        retries = Retry(total=self.retries,
                        backoff_factor=0.1,
                        status_forcelist=[500],
                        raise_on_status=False)
        websession.mount('https://', HTTPAdapter(max_retries=retries))
        websession.headers = CaseInsensitiveDict({
            'user-agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 '
                          'Chrome/74.0.3729.185 Mobile Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                      'application/signed-exchange;v=b3',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'gzip, deflate',
            'x-requested-with': 'de.volkswagen.carnet.eu.eremote',
            'upgrade-insecure-requests': '1',
        })

        while True:
            loginFormResponse: requests.Response = websession.get(authorizationUrl, allow_redirects=False)
            if loginFormResponse.status_code == requests.codes['ok']:
                break
            elif loginFormResponse.status_code == requests.codes['found']:
                if 'Location' in loginFormResponse.headers:
                    authorizationUrl = loginFormResponse.headers['Location']
                else:
                    raise APICompatibilityError('Forwarding without Location in Header')
            elif loginFormResponse.status_code == requests.codes['internal_server_error']:
                raise RetrievalError('Temporary server error during login')
            else:
                raise APICompatibilityError('Retrieving credentials page was not successfull,'
                                            f' status code: {loginFormResponse.status_code}')
        # Find login form on page to obtain inputs
        emailFormRegex = r'<form.+id=\"emailPasswordForm\".*action=\"(?P<formAction>[^\"]+)\"[^>]*>' \
            r'(?P<formContent>.+?(?=</form>))</form>'
        match: Optional[Match[str]] = re.search(emailFormRegex, loginFormResponse.text, flags=re.DOTALL)
        if match is None:
            raise AuthentificationError('No login email form found')
        # retrieve target url from form
        target: str = match.groupdict()['formAction']

        # Find all inputs and put those in formData dictionary
        inputRegex = r'<input[\\n\\r\s][^/]*name=\"(?P<name>[^\"]+)\"([\\n\\r\s]value=\"(?P<value>[^\"]+)\")?[^/]*/>'
        formData: Dict[str, str] = {}
        for match in re.finditer(inputRegex, match.groupdict()['formContent']):
            if match.groupdict()['name']:
                formData[match.groupdict()['name']] = match.groupdict()['value']
        if not all(x in ['_csrf', 'registerFlow', 'relayState', 'hmac', 'identifier'] for x in formData):
            raise AuthentificationError('Could not find all required input fields in login page')

        # Set email to the provided username
        formData['identifier'] = self.sessionuser.username

        # build url from form action
        login2Url: str = 'https://identity.vwgroup.io' + target

        loginHeadersForm: CaseInsensitiveDict = websession.headers.copy()
        loginHeadersForm['Content-Type'] = 'application/x-www-form-urlencoded'

        # Post form content and retrieve credentials page
        login2Response: requests.Response = websession.post(login2Url, headers=loginHeadersForm, data=formData, allow_redirects=True)

        if login2Response.status_code != requests.codes['ok']:  # pylint: disable=E1101
            if login2Response.status_code == requests.codes['internal_server_error']:
                raise RetrievalError('Temporary server error during login')
            raise AuthentificationError('Retrieving credentials page was not successfull,'
                                        f' status code: {login2Response.status_code}')

        credentialsTemplateRegex = r'<script>\s+window\._IDK\s+=\s+\{\s' \
            r'(?P<templateModel>.+?(?=\s+\};?\s+</script>))\s+\};?\s+</script>'
        match = re.search(credentialsTemplateRegex, login2Response.text, flags=re.DOTALL)
        if match is None:
            raise AuthentificationError('No credentials form found')
        if match.groupdict()['templateModel']:
            lineRegex = r'\s*(?P<name>[^\:]+)\:\s+[\'\{]?(?P<value>.+)[\'\}][,]?'
            form2Data: Dict[str, str] = {}
            for match in re.finditer(lineRegex, match.groupdict()['templateModel']):
                if match.groupdict()['name'] == 'templateModel':
                    templateModelString = '{' + match.groupdict()['value'] + '}'
                    if templateModelString.endswith(','):
                        templateModelString = templateModelString[:-len(',')]
                    templateModel = json.loads(templateModelString)
                    if 'relayState' in templateModel:
                        form2Data['relayState'] = templateModel['relayState']
                    if 'hmac' in templateModel:
                        form2Data['hmac'] = templateModel['hmac']
                    if 'emailPasswordForm' in templateModel and 'email' in templateModel['emailPasswordForm']:
                        form2Data['email'] = templateModel['emailPasswordForm']['email']
                    if 'error' in templateModel and templateModel['error'] is not None:
                        if templateModel['error'] == 'validator.email.invalid':
                            raise AuthentificationError('Error during login, email invalid')
                        raise AuthentificationError(f'Error during login: {templateModel["error"]}')
                    if 'registerCredentialsPath' in templateModel and templateModel['registerCredentialsPath'] == 'register':
                        raise AuthentificationError(f'Error during login, account {self.sessionuser.username} does not exist')
                    if 'errorCode' in templateModel:
                        raise AuthentificationError('Error during login, is the username correct?')
                    if 'postAction' in templateModel:
                        target = templateModel['postAction']
                    else:
                        raise APICompatibilityError('Form does not contain postAction')
                elif match.groupdict()['name'] == 'csrf_token':
                    form2Data['_csrf'] = match.groupdict()['value']
        form2Data['password'] = self.sessionuser.password
        if not all(x in ['_csrf', 'relayState', 'hmac', 'email', 'password'] for x in form2Data):
            raise AuthentificationError('Could not find all required input fields in credentials page')

        login3Url = f'https://identity.vwgroup.io/signin-service/v1/{self.client_id}/{target}'

        # Post form content and retrieve userId in forwarding Location
        login3Response: requests.Response = websession.post(login3Url, headers=loginHeadersForm, data=form2Data, allow_redirects=False)
        if login3Response.status_code not in (requests.codes['found'], requests.codes['see_other']):
            if login3Response.status_code == requests.codes['internal_server_error']:
                raise RetrievalError('Temporary server error during login')
            raise AuthentificationError('Forwarding expected (status code 302),'
                                        f' but got status code {login3Response.status_code}')
        if 'Location' not in login3Response.headers:
            raise AuthentificationError('No url for forwarding in response headers')

        # Parse parametes from forwarding url
        params: Dict[str, str] = dict(parse_qsl(urlsplit(login3Response.headers['Location']).query))

        # Check if error
        if 'error' in params and params['error']:
            errorMessages: Dict[str, str] = {
                'login.errors.password_invalid': 'Password is invalid',
                'login.error.throttled': 'Login throttled, probably too many wrong logins. You have to wait some'
                                         ' minutes until a new login attempt is possible'
            }
            if params['error'] in errorMessages:
                error = errorMessages[params['error']]
            else:
                error = params['error']
            raise AuthentificationError(error)

        # Check for user id
        if 'userId' not in params or not params['userId']:
            if 'updated' in params and params['updated'] == 'dataprivacy':
                raise AuthentificationError('You have to login at myvolkswagen.de and accept the terms and conditions')
            raise AuthentificationError('No user id provided')
        self.__userId = params['userId']  # pylint: disable=unused-private-member

        # Now follow the forwarding until forwarding URL starts with 'weconnect://authenticated#'
        afterLoginUrl: str = login3Response.headers['Location']

        while True:
            if 'consent' in afterLoginUrl:
                consentURL = afterLoginUrl
            afterLoginResponse = self.get(afterLoginUrl, allow_redirects=False, access_type=AccessType.NONE)
            if afterLoginResponse.status_code == requests.codes['internal_server_error']:
                raise RetrievalError('Temporary server error during login')

            if 'Location' not in afterLoginResponse.headers:
                if consentURL is not None:
                    raise AuthentificationError('It seems like you need to accept the terms and conditions for the WeConnect ID service.'
                                                f' Try to visit the URL "{consentURL}" or log into the WeConnect ID smartphone app')
                raise AuthentificationError('No Location for forwarding in response headers')

            afterLoginUrl = afterLoginResponse.headers['Location']

            if afterLoginUrl.startswith(self.redirect_uri):
                break

        if afterLoginUrl.startswith(self.redirect_uri + '#'):
            queryurl = afterLoginUrl.replace(self.redirect_uri + '#', 'https://egal?')
        else:
            queryurl = afterLoginUrl
        return queryurl

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
