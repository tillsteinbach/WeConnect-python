from typing import Any, Dict
from urllib3.util.retry import Retry
from urllib.parse import parse_qsl, urlparse, urlsplit, urljoin


import requests
from requests.adapters import HTTPAdapter
from requests.models import CaseInsensitiveDict

from weconnect.auth.auth_util import CredentialsFormParser, HTMLFormParser, TermsAndConditionsFormParser
from weconnect.auth.openid_session import OpenIDSession
from weconnect.errors import APICompatibilityError, AuthentificationError, RetrievalError


class VWWebSession(OpenIDSession):
    def __init__(self, sessionuser, acceptTermsOnLogin=False, **kwargs):
        super(VWWebSession, self).__init__(**kwargs)
        self.sessionuser = sessionuser
        self.acceptTermsOnLogin = acceptTermsOnLogin

        # Set up the web session
        retries = Retry(
            total=self.retries,
            backoff_factor=0.1,
            status_forcelist=[500],
            raise_on_status=False
        )

        self.websession: requests.Session = requests.Session()
        self.websession.proxies.update(self.proxies)
        self.websession.mount('https://', HTTPAdapter(max_retries=retries))
        self.websession.headers = CaseInsensitiveDict({
            'user-agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 '
                          'Chrome/74.0.3729.185 Mobile Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                      'application/signed-exchange;v=b3',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'gzip, deflate',
            'x-requested-with': 'de.volkswagen.carnet.eu.eremote',
            'upgrade-insecure-requests': '1',
        })

    def doWebAuth(self, url: str) -> str:
        # Get the login form
        emailForm = self._get_login_form(url)

        # Set email to the provided username
        emailForm.data['email'] = self.sessionuser.username

        # Get password form
        passwordForm = self._get_password_form(
            urljoin('https://identity.vwgroup.io', emailForm.target),
            emailForm.data
        )

        # Set credentials
        passwordForm.data['email'] = self.sessionuser.username
        passwordForm.data['password'] = self.sessionuser.password

        # Log in and get the redirect URL
        url = self._handle_login(
            f'https://identity.vwgroup.io/signin-service/v1/{self.client_id}/{passwordForm.target}',
            passwordForm.data
        )

        # Check URL for terms and conditions
        while True:
            if url.startswith(self.redirect_uri):
                break

            url = urljoin('https://identity.vwgroup.io', url)

            if 'terms-and-conditions' in url:
                if self.acceptTermsOnLogin:
                    url = self._handle_consent_form(url)
                else:
                    raise AuthentificationError(f'It seems like you need to accept the terms and conditions. '
                                                f'Try to visit the URL "{url}" or log into smartphone app.')

            response = self.websession.get(url, allow_redirects=False)
            if response.status_code == requests.codes['internal_server_error']:
                raise RetrievalError('Temporary server error during login')

            if 'Location' not in response.headers:
                raise APICompatibilityError('Forwarding without Location in headers')

            url = response.headers['Location']

        return url.replace(self.redirect_uri + '#', 'https://egal?')

    def _get_login_form(self, url: str) -> HTMLFormParser:
        while True:
            response = self.websession.get(url, allow_redirects=False)
            if response.status_code == requests.codes['ok']:
                break

            if response.status_code in (requests.codes['found'], requests.codes['see_other']):
                if 'Location' not in response.headers:
                    raise APICompatibilityError('Forwarding without Location in headers')

                url = response.headers['Location']
                continue

            raise APICompatibilityError(f'Retrieving login page was not successful, '
                                        f'status code: {response.status_code}')

        # Find login form on page to obtain inputs
        emailForm = HTMLFormParser(form_id='emailPasswordForm')
        emailForm.feed(response.text)

        if not emailForm.target or not all(x in emailForm.data for x in ['_csrf', 'relayState', 'hmac', 'email']):
            raise APICompatibilityError('Could not find all required input fields on login page')

        return emailForm

    def _get_password_form(self, url: str, data: Dict[str, Any]) -> CredentialsFormParser:
        response = self.websession.post(url, data=data, allow_redirects=True)
        if response.status_code != requests.codes['ok']:
            raise APICompatibilityError(f'Retrieving credentials page was not successful, '
                                        f'status code: {response.status_code}')

        # Find login form on page to obtain inputs
        credentialsForm = CredentialsFormParser()
        credentialsForm.feed(response.text)

        if not credentialsForm.target or not all(x in credentialsForm.data for x in ['relayState', 'hmac', '_csrf']):
            raise APICompatibilityError('Could not find all required input fields on credentials page')

        if credentialsForm.data.get('error', None) is not None:
            if credentialsForm.data['error'] == 'validator.email.invalid':
                raise AuthentificationError('Error during login, email invalid')
            raise AuthentificationError(f'Error during login: {credentialsForm.data["error"]}')

        if 'errorCode' in credentialsForm.data:
            raise AuthentificationError('Error during login, is the username correct?')

        if credentialsForm.data.get('registerCredentialsPath', None) == 'register':
            raise AuthentificationError(f'Error during login, account {self.sessionuser.username} does not exist')

        return credentialsForm

    def _handle_login(self, url: str, data: Dict[str, Any]) -> str:
        response: requests.Response = self.websession.post(url, data=data, allow_redirects=False)

        if response.status_code == requests.codes['internal_server_error']:
            raise RetrievalError('Temporary server error during login')

        if response.status_code not in (requests.codes['found'], requests.codes['see_other']):
            raise APICompatibilityError(f'Forwarding expected (status code 302), '
                                        f'but got status code {response.status_code}')

        if 'Location' not in response.headers:
            raise APICompatibilityError('Forwarding without Location in headers')

        # Parse parameters from forwarding url
        params: Dict[str, str] = dict(parse_qsl(urlsplit(response.headers['Location']).query))

        # Check for login error
        if 'error' in params and params['error']:
            errorMessages: Dict[str, str] = {
                'login.errors.password_invalid': 'Password is invalid',
                'login.error.throttled': 'Login throttled, probably too many wrong logins. You have to wait '
                                         'a few minutes until a new login attempt is possible'
            }

            raise AuthentificationError(errorMessages.get(params['error'], params['error']))

        # Check for user ID
        if 'userId' not in params or not params['userId']:
            if 'updated' in params and params['updated'] == 'dataprivacy':
                raise AuthentificationError('You have to login at myvolkswagen.de and accept the terms and conditions')
            raise APICompatibilityError('No user ID provided')

        self.userId = params['userId']  # pylint: disable=unused-private-member
        return response.headers['Location']

    def _handle_consent_form(self, url: str) -> str:
        response = self.websession.get(url, allow_redirects=False)
        if response.status_code == requests.codes['internal_server_error']:
            raise RetrievalError('Temporary server error during login')

        # Find form on page to obtain inputs
        tcForm = TermsAndConditionsFormParser()
        tcForm.feed(response.text)

        # Remove query from URL
        url = urlparse(response.url)._replace(query='').geturl()

        response = self.websession.post(url, data=tcForm.data, allow_redirects=False)
        if response.status_code == requests.codes['internal_server_error']:
            raise RetrievalError('Temporary server error during login')

        if response.status_code not in (requests.codes['found'], requests.codes['see_other']):
            raise APICompatibilityError('Forwarding expected (status code 302), '
                                        f'but got status code {response.status_code}')

        if 'Location' not in response.headers:
            raise APICompatibilityError('Forwarding without Location in headers')

        return response.headers['Location']
