from typing import Any, Dict
from urllib3.util.retry import Retry
from urllib.parse import parse_qsl, urlparse, urlsplit, urljoin

import logging

import requests
from requests.adapters import HTTPAdapter
from requests.models import CaseInsensitiveDict

from weconnect.auth.auth_util import CredentialsFormParser, HTMLFormParser, TermsAndConditionsFormParser
from weconnect.auth.openid_session import OpenIDSession
from weconnect.errors import APICompatibilityError, AuthentificationError, RetrievalError


LOG = logging.getLogger("weconnect")


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
            'user-agent': 'Volkswagen/3.51.1-android/14',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                      'application/signed-exchange;v=b3',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'gzip, deflate',
            'x-requested-with': 'de.volkswagen.carnet.eu.eremote',
            'x-android-package-name': 'com.volkswagen.weconnect',
            'upgrade-insecure-requests': '1',
        })

    def doWebAuth(self, url: str) -> str:
        # Check if we already have the final OAuth callback URL
        if url.startswith('weconnect://authenticated'):
            LOG.info("Already have OAuth callback URL with tokens, returning immediately")
            return url.replace('weconnect://authenticated#', 'https://egal?')
        
        # Get the login form
        emailForm = self._get_login_form(url)

        if emailForm:
            # Legacy authentication flow
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
        else:
            # New authentication flow
            url = self._handle_new_auth_flow(url)

        # Check URL for terms and conditions
        while True:
            LOG.debug(f"DEBUG [do_web_auth]: Processing URL in while loop: {url[:150]}")

            # Check for custom scheme FIRST, before any URL manipulation
            if url.startswith('weconnect://authenticated'):
                LOG.info(f"Reached final OAuth callback URL with tokens")
                LOG.debug(f"DEBUG [do_web_auth]: Found weconnect://authenticated URL, breaking loop to return transformed URL")
                break

            # Also check for redirect_uri if it's a custom scheme
            if self.redirect_uri and url.startswith(self.redirect_uri):
                LOG.info(f"Reached redirect URI: {self.redirect_uri}")
                LOG.debug(f"DEBUG [do_web_auth]: Found redirect_uri URL, breaking loop")
                break

            # Check for any other custom scheme to prevent HTTP requests
            if url.startswith('weconnect://'):
                LOG.info(f"Found custom scheme URL, treating as final URL")
                LOG.debug(f"DEBUG [do_web_auth]: Found weconnect:// URL (non-authenticated), returning with transformation: {url[:100]}")
                return url.replace('weconnect://', 'https://egal?')

            # Only join URLs that are not custom schemes
            url = urljoin('https://identity.vwgroup.io', url)

            if 'terms-and-conditions' in url:
                if self.acceptTermsOnLogin:
                    url = self._handle_consent_form(url)
                else:
                    raise AuthentificationError(f'It seems like you need to accept the terms and conditions. '
                                                f'Try to visit the URL "{url}" or log into smartphone app.')

            LOG.debug(f"DEBUG [do_web_auth]: Making HTTP GET request to: {url[:100]}")
            response = self.websession.get(url, allow_redirects=False)
            if response.status_code == requests.codes['internal_server_error']:
                raise RetrievalError('Temporary server error during login')

            if 'Location' not in response.headers:
                raise APICompatibilityError('Forwarding without Location in headers')

            url = response.headers['Location']
            LOG.debug(f"DEBUG [do_web_auth]: Got Location header, new URL: {url[:100]}")

            # Check again after getting new URL from Location header
            if url.startswith('weconnect://authenticated'):
                LOG.info(f"OAuth flow completed, received callback URL with tokens")
                LOG.debug(f"DEBUG [do_web_auth]: Found weconnect://authenticated in Location header, breaking loop")
                break

            # Check for ANY weconnect:// scheme to prevent invalid requests
            if url.startswith('weconnect://'):
                LOG.info(f"OAuth flow reached custom scheme URL")
                LOG.debug(f"DEBUG [do_web_auth]: Found weconnect:// in Location header, breaking loop: {url[:100]}")
                break

            # Also check for redirect_uri if it's set
            if self.redirect_uri and url.startswith(self.redirect_uri):
                LOG.info(f"OAuth flow completed, received redirect URI")
                LOG.debug(f"DEBUG [do_web_auth]: Found redirect_uri in Location header: {url[:100]}")
                break

        LOG.debug(f"DEBUG [do_web_auth]: Exited while loop, final URL before transformation: {url[:150]}")

        # Handle the transformation based on the URL pattern
        if url.startswith('weconnect://authenticated#'):
            # Transform weconnect://authenticated# to https://egal?
            transformed_url = url.replace('weconnect://authenticated#', 'https://egal?')
            LOG.debug(f"DEBUG [do_web_auth]: Transformed weconnect://authenticated# URL to: {transformed_url[:150]}")
            return transformed_url
        elif self.redirect_uri and url.startswith(self.redirect_uri + '#'):
            # Transform redirect_uri# to https://egal?
            transformed_url = url.replace(self.redirect_uri + '#', 'https://egal?')
            LOG.debug(f"DEBUG [do_web_auth]: Transformed redirect_uri# URL to: {transformed_url[:150]}")
            return transformed_url
        else:
            LOG.warning(f"DEBUG [do_web_auth]: URL doesn't match expected patterns, returning as-is: {url[:150]}")
            return url

    def _get_login_form(self, url: str) -> HTMLFormParser:
        # Check for custom URL schemes before making HTTP requests
        if url.startswith('weconnect://'):
            LOG.info(f"[_get_login_form] Custom scheme URL detected, skipping legacy auth flow")
            LOG.debug(f"DEBUG [_get_login_form]: Custom scheme URL detected, returning None: {url[:150]}")
            return None

        # Also check if URL contains tokens already (might be a callback URL)
        if '#access_token=' in url or '#code=' in url:
            LOG.info(f"[_get_login_form] URL already contains OAuth tokens, skipping legacy auth flow")
            LOG.debug(f"DEBUG [_get_login_form]: URL contains tokens, returning None: {url[:150]}")
            return None
        while True:
            LOG.debug(f"DEBUG [_get_login_form]: Attempting to fetch: {url[:100]}")

            # Check for custom URL schemes during redirect loop
            if url.startswith('weconnect://'):
                LOG.info(f"[_get_login_form] Reached OAuth callback URL during redirects: {url[:100]}")
                LOG.debug(f"DEBUG [_get_login_form]: Custom scheme URL reached in redirect loop, returning None")
                return None
            
            response = self.websession.get(url, allow_redirects=False)
            if response.status_code == requests.codes['ok']:
                break

            if response.status_code in (requests.codes['found'], requests.codes['see_other']):
                if 'Location' not in response.headers:
                    raise APICompatibilityError('Forwarding without Location in headers')

                # Resolve relative URL to absolute URL
                url = urljoin(url, response.headers['Location'])

                # Check if the new URL is a custom scheme URL
                if url.startswith('weconnect://'):
                    LOG.info(f"[_get_login_form] OAuth callback URL found in Location header: {url[:100]}")
                    LOG.debug(f"DEBUG [_get_login_form]: Custom scheme URL in Location header, returning None")
                    return None
                continue

            raise APICompatibilityError(f'Retrieving login page was not successful, '
                                        f'status code: {response.status_code}')

        # Find login form on page to obtain inputs
        emailForm = HTMLFormParser(form_id='emailPasswordForm')
        emailForm.feed(response.text)

        if not emailForm.target or not all(x in emailForm.data for x in ['_csrf', 'relayState', 'hmac', 'email']):
            # Return None to indicate legacy form not found, new flow should be used
            return None

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

    def _handle_new_auth_flow(self, url: str) -> str:
        """
        Handle the new authentication flow when legacy form is not available.
        
        Args:
            url (str): The authorization URL.
            
        Returns:
            str: The redirect URL after successful authentication.
            
        Raises:
            AuthenticationError: If authentication fails.
            APICompatibilityError: If there are issues with the authentication flow.
        """
        import re

        # Check if we already have the OAuth callback URL
        if url.startswith('weconnect://authenticated'):
            LOG.info("OAuth callback URL already present in new auth flow, returning immediately")
            return url

        # Get the authorization page (manually follow redirects to avoid custom scheme issues)
        max_initial_redirects = 5
        while max_initial_redirects > 0:
            # Check for custom scheme before making request
            if url.startswith('weconnect://'):
                LOG.info(f"Found custom scheme URL during initial auth page fetch")
                return url

            response = self.websession.get(url, allow_redirects=False)

            if response.status_code == requests.codes['ok']:
                break

            if response.status_code in (requests.codes['found'], requests.codes['see_other']):
                if 'Location' not in response.headers:
                    raise APICompatibilityError('Forwarding without Location in headers')
                url = urljoin(url, response.headers['Location'])
                max_initial_redirects -= 1
                continue

            raise APICompatibilityError(f'Failed to fetch authorization page, status code: {response.status_code}')

        if max_initial_redirects == 0:
            raise APICompatibilityError('Too many redirects while fetching authorization page')

        # Extract state token using regex
        state_match = re.search(r'<input[^>]*name="state"[^>]*value="([^"]*)"', response.text)
        state = state_match.group(1) if state_match else None

        if not state:
            raise APICompatibilityError('Could not find state token in authorization page')

        # Create login form data
        login_form = {
            'username': self.sessionuser.username,
            'password': self.sessionuser.password,
            'state': state
        }

        # Post to login URL
        login_url = f'https://identity.vwgroup.io/u/login?state={state}'
        LOG.debug(f"Posting to login URL: {login_url}")
        response = self.websession.post(login_url, data=login_form, allow_redirects=False)

        if response.status_code not in (requests.codes['found'], requests.codes['see_other']):
            raise AuthenticationError(f'Login failed with status code: {response.status_code}')

        if 'Location' not in response.headers:
            raise APICompatibilityError('No Location header in login response')

        # Follow redirects to get the final URL with authorization code
        redirect_url = response.headers['Location']
        LOG.debug(f"DEBUG [_handle_new_auth_flow]: Starting redirect follow loop with URL: {redirect_url[:150]}")
        max_depth = 10
        while max_depth > 0:
            LOG.debug(f"DEBUG [_handle_new_auth_flow]: Loop iteration, max_depth={max_depth}, URL: {redirect_url[:150]}")

            # Check for custom scheme IMMEDIATELY before any processing
            if redirect_url.startswith('weconnect://authenticated'):
                LOG.info(f"Successfully reached OAuth callback URL with custom scheme")
                LOG.debug(f"DEBUG [_handle_new_auth_flow]: Found weconnect://authenticated URL with tokens, returning immediately")
                return redirect_url

            # Also check for any weconnect:// scheme
            if redirect_url.startswith('weconnect://'):
                LOG.info(f"Found weconnect:// custom scheme URL")
                LOG.debug(f"DEBUG [_handle_new_auth_flow]: Found weconnect:// URL, returning immediately: {redirect_url[:150]}")
                return redirect_url

            if max_depth == 0:
                raise APICompatibilityError('Too many redirects in new auth flow')

            # Only process non-custom scheme URLs
            redirect_url = urljoin('https://identity.vwgroup.io', redirect_url)
            LOG.debug(f"DEBUG [_handle_new_auth_flow]: URL after urljoin: {redirect_url[:150]}")

            LOG.debug(f"DEBUG [_handle_new_auth_flow]: Making HTTP GET request to: {redirect_url[:100]}")
            response = self.websession.get(redirect_url, allow_redirects=False)

            if response.status_code == requests.codes['internal_server_error']:
                raise RetrievalError('Temporary server error during new auth flow')

            if 'Location' not in response.headers:
                LOG.debug(f"DEBUG [_handle_new_auth_flow]: No Location header in response, status code: {response.status_code}")
                raise APICompatibilityError('No Location header in redirect')

            redirect_url = response.headers['Location']
            LOG.debug(f"DEBUG [_handle_new_auth_flow]: Got Location header: {redirect_url[:150]}")

            # Check again after getting new redirect URL
            if redirect_url.startswith('weconnect://authenticated'):
                LOG.info(f"Successfully reached OAuth callback URL with custom scheme after redirect")
                LOG.debug(f"DEBUG [_handle_new_auth_flow]: Found weconnect://authenticated URL after redirect, returning immediately")
                return redirect_url

            # Also check for any weconnect:// scheme
            if redirect_url.startswith('weconnect://'):
                LOG.info(f"Found weconnect:// custom scheme URL after redirect")
                LOG.debug(f"DEBUG [_handle_new_auth_flow]: Found weconnect:// URL after redirect, returning: {redirect_url[:150]}")
                return redirect_url

            max_depth -= 1

        LOG.debug(f"DEBUG [_handle_new_auth_flow]: Exiting redirect loop after max iterations, returning URL: {redirect_url[:150]}")
        return redirect_url

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
