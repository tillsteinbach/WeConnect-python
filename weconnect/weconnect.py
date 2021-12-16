from __future__ import annotations
from typing import Dict, List, Set, Tuple, Callable, Any, Optional, Union, cast, Match

import os
import string
import random
import re
import locale
import logging
import threading
import json
from datetime import datetime, timedelta, timezone
from urllib import parse

import requests
from urllib3.util.retry import Retry
from requests.cookies import RequestsCookieJar
from requests.structures import CaseInsensitiveDict
from requests.adapters import HTTPAdapter

from weconnect.elements.vehicle import Vehicle
from weconnect.elements.charging_station import ChargingStation
from weconnect.addressable import AddressableLeaf, AddressableObject, AddressableDict
from weconnect.errors import APICompatibilityError, AuthentificationError, RetrievalError
from weconnect.weconnect_errors import ErrorEventType

LOG = logging.getLogger("weconnect")


class BearerAuth(requests.auth.AuthBase):
    """Requests auth class for Bearer token authentification header"""

    def __init__(self, token: str) -> None:
        """Intialize authentification class from token

        Args:
            token (str): token to be used
        """
        self.token = token

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        """Internally used in requests to prepare a request with authentification

        Args:
            r (requests.PreparedRequest): The request to prepare

        Returns:
            requests.PreparedRequest: Request with authentification header
        """
        r.headers["authorization"] = "Bearer " + self.token
        return r


class DateTimeEncoder(json.JSONEncoder):
    """Datetime object encode used for json serialization"""

    def default(self, o: datetime) -> str:
        """Serialize datetime object to isodate string

        Args:
            o (datetime): datetime object

        Returns:
            str: object represented as isoformat string
        """
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)


class WeConnect(AddressableObject):  # pylint: disable=too-many-instance-attributes
    """Main class used to interact with WeConnect"""

    DEFAULT_OPTIONS: Dict[str, Any] = {
        "headers": CaseInsensitiveDict({
            'accept': '*/*',
            'content-type': 'application/json',
            'content-version': '1',
            'x-newrelic-id': 'VgAEWV9QDRAEXFlRAAYPUA==',
            'user-agent': 'WeConnect/5 CFNetwork/1206 Darwin/20.1.0',
            'accept-language': 'de-de',
        }),
        "loginHeaders": CaseInsensitiveDict({
            'user-agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 '
                          'Chrome/74.0.3729.185 Mobile Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                      'application/signed-exchange;v=b3',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'gzip, deflate',
            'x-requested-with': 'de.volkswagen.carnet.eu.eremote',
            'upgrade-insecure-requests': '1',
        }),
        "refreshBeforeExpires": 30
    }

    def __init__(  # noqa: C901 # pylint: disable=too-many-arguments
        self,
        username: str,
        password: str,
        tokenfile: Optional[str] = None,
        updateAfterLogin: bool = True,
        loginOnInit: bool = True,
        refreshTokens: bool = True,
        fixAPI: bool = True,
        maxAge: Optional[int] = None,
        maxAgePictures: Optional[int] = None,
        updateCapabilities: bool = True,
        updatePictures: bool = True,
        numRetries: int = 3
    ) -> None:
        """Initialize WeConnect interface. If loginOnInit is true the user will be tried to login.
           If loginOnInit is true also an initial fetch of data is performed.

        Args:
            username (str): Username used with WeConnect. This is your volkswagen user.
            password (str): Password used with WeConnect. This is your volkswagen password.
            tokenfile (Optional[str], optional): Optional file to read/write token from/to. Defaults to None.
            updateAfterLogin (bool, optional): Update data from WeConnect after logging in (If set to false, update needs to be called manually).
            Defaults to True.
            loginOnInit (bool, optional): Login after initialization (If set to false, login needs to be called manually). Defaults to True.
            refreshTokens (bool, optional): Refresh tokens every 3600 seconds. Defaults to True.
            fixAPI (bool, optional): Automatically fix known issues with the WeConnect responses. Defaults to True.
            maxAge (Optional[int], optional): Maximum age of the cache before date is fetched again. None means no caching. Defaults to None.
            maxAgePictures (Optional[int], optional):  Maximum age of the pictures in the cache before date is fetched again. None means no caching.
            Defaults to None.
            updateCapabilities (bool, optional): Also update the information about the cars capabilities. Defaults to True.
            updatePictures (bool, optional):  Also fetch and update pictures. Defaults to True.
            numRetries (int, optional): Number of retries when http requests are failing. Defaults to 3.
        """
        super().__init__(localAddress='', parent=None)
        self.username: str = username
        self.password: str = password
        # TODO: Named Tupel instead!
        self.__token: Dict[str, Optional[Union[str, datetime]]] = {'type': None, 'token': None, 'expires': None}
        self.__aToken: Dict[str, Optional[Union[str, datetime]]] = {'type': None, 'token': None, 'expires': None}
        self.__rToken: Dict[str, Optional[Union[str, datetime]]] = {'type': None, 'token': None, 'expires': None}
        self.__userId: Optional[str] = None  # pylint: disable=unused-private-member
        self.__session: requests.Session = requests.Session()
        self.__refreshTimer: Optional[threading.Timer] = None
        self.__vehicles: AddressableDict[str, Vehicle] = AddressableDict(localAddress='vehicles', parent=self)
        self.__stations: AddressableDict[str, ChargingStation] = AddressableDict(localAddress='chargingStations', parent=self)
        self.__cache: Dict[str, Any] = {}
        self.fixAPI: bool = fixAPI
        self.maxAge: Optional[int] = maxAge
        self.maxAgePictures: Optional[int] = maxAgePictures
        self.latitude: Optional[float] = None
        self.longitude: Optional[float] = None
        self.searchRadius: Optional[int] = None
        self.market: Optional[str] = None
        self.useLocale: Optional[str] = locale.getlocale()[0]
        self.__elapsed: List[timedelta] = []

        self.__errorObservers: Set[Tuple[Callable[[Optional[Any], ErrorEventType], None], ErrorEventType]] = set()

        self.__session.headers = self.DEFAULT_OPTIONS['headers']

        # Retry on internal server error (500)
        retries = Retry(total=numRetries,
                        backoff_factor=0.1,
                        status_forcelist=[500],
                        raise_on_status=False)
        self.__session.mount('https://', HTTPAdapter(max_retries=retries))

        self.tokenfile: Optional[str] = tokenfile
        if self.tokenfile:
            try:
                with open(self.tokenfile, 'r', encoding='utf8') as file:
                    tokens: RequestsCookieJar = requests.utils.cookiejar_from_dict(json.load(file))

                if 'idToken' in tokens and all(key in tokens['idToken'] for key in ('type', 'token', 'expires')):
                    self.__token['type'] = tokens['idToken']['type']
                    self.__token['token'] = tokens['idToken']['token']
                    self.__token['expires'] = datetime.fromisoformat(tokens['idToken']['expires'])
                    self.__session.auth = BearerAuth(cast(str, self.__token['token']))
                else:
                    LOG.info('Could not use token from file %s (does not contain a token)', self.tokenfile)

                if 'accessToken' in tokens and all(key in tokens['accessToken'] for key in ('type', 'token', 'expires')):
                    self.__aToken['type'] = tokens['accessToken']['type']
                    self.__aToken['token'] = tokens['accessToken']['token']
                    self.__aToken['expires'] = datetime.fromisoformat(tokens['accessToken']['expires'])
                    self.__session.auth = BearerAuth(cast(str, self.__aToken['token']))
                else:
                    LOG.info('Could not use token from file %s (does not contain a token)', self.tokenfile)

                if 'refreshToken' in tokens and all(key in tokens['refreshToken'] for key in ('type', 'token', 'expires')):
                    self.__rToken['type'] = tokens['refreshToken']['type']
                    self.__rToken['token'] = tokens['refreshToken']['token']
                    self.__rToken['expires'] = datetime.fromisoformat(tokens['refreshToken']['expires'])
                else:
                    LOG.info('Could not use refreshToken from file %s (does not contain a token)', self.tokenfile)

                # Refresh tokens once
                if loginOnInit or refreshTokens:
                    self.__refreshToken()

            except json.JSONDecodeError as err:
                LOG.info('Could not use token from file %s (%s)', tokenfile, err.msg)
            except FileNotFoundError as err:
                LOG.info('Could not use token from file %s (%s)', tokenfile, err)

        if loginOnInit:
            if self.__token['expires'] is None or cast(datetime, self.__token['expires']) <= \
                    datetime.utcnow().replace(tzinfo=timezone.utc):
                self.login()
            else:
                LOG.info('Login not necessary, token still valid')

        if updateAfterLogin:
            self.update(updateCapabilities=updateCapabilities, updatePictures=updatePictures)

    @property
    def session(self) -> requests.Session:
        return self.__session

    @property
    def cache(self) -> Dict[str, Any]:
        return self.__cache

    def persistTokens(self) -> None:
        if self.tokenfile:
            try:
                with open(self.tokenfile, 'w', encoding='utf8') as file:
                    json.dump({'idToken': self.__token, 'refreshToken': self.__rToken, 'accessToken': self.__aToken}, file, cls=DateTimeEncoder)
                LOG.info('Writing tokenfile %s', self.tokenfile)
            except ValueError as err:  # pragma: no cover
                LOG.info('Could not write tokenfile %s (%s)', self.tokenfile, err)

    def persistCacheAsJson(self, filename: str) -> None:
        with open(filename, 'w', encoding='utf8') as file:
            json.dump(self.__cache, file, cls=DateTimeEncoder)
        LOG.info('Writing cachefile %s', filename)

    def fillCacheFromJson(self, filename: str, maxAge: int, maxAgePictures: Optional[int] = None) -> None:
        self.maxAge = maxAge
        if maxAgePictures is None:
            self.maxAgePictures = maxAge
        else:
            self.maxAgePictures = maxAgePictures

        try:
            with open(filename, 'r', encoding='utf8') as file:
                self.__cache = json.load(file)
        except json.decoder.JSONDecodeError:
            LOG.error('Cachefile %s seems corrupted will delete it and try to create a new one. '
                      'If this problem persists please check if a problem with your disk exists.', filename)
            os.remove(filename)
        LOG.info('Reading cachefile %s', filename)

    def fillCacheFromJsonString(self, jsonString, maxAge: int, maxAgePictures: Optional[int] = None) -> None:
        self.maxAge = maxAge
        if maxAgePictures is None:
            self.maxAgePictures = maxAge
        else:
            self.maxAgePictures = maxAgePictures

        self.__cache = json.loads(jsonString)
        LOG.info('Reading cache from string')

    def clearCache(self) -> None:
        self.__cache.clear()
        LOG.info('Clearing cache')

    def login(self) -> None:  # noqa: C901 # pylint: disable=R0914, R0912, too-many-statements
        # Try to access page to be redirected to login form
        tryLoginUrl: str = f'https://login.apps.emea.vwapps.io/authorize?nonce=' \
            f'{"".join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=16))}' \
            '&redirect_uri=weconnect://authenticated'

        tryLoginResponse: requests.Response = self.__session.get(tryLoginUrl, allow_redirects=False)
        if tryLoginResponse.status_code != requests.codes['see_other']:
            raise APICompatibilityError('Forwarding to login page expected (status code 303),'
                                        f' but got status code {tryLoginResponse.status_code}')
        if 'Location' not in tryLoginResponse.headers:
            raise APICompatibilityError('No url for forwarding in response headers')
        # Login url is in response headers when response has status code see_others (303)
        loginUrl: str = tryLoginResponse.headers['Location']

        if loginUrl.startswith('weconnect://authenticated#'):
            params = dict(parse.parse_qsl(parse.urlsplit(loginUrl.replace('authenticated#', 'authenticated?')).query))
        else:
            # Retrieve login page
            loginResponse: requests.Response = self.__session.get(loginUrl, headers=self.DEFAULT_OPTIONS['loginHeaders'], allow_redirects=True)
            if loginResponse.status_code != requests.codes['ok']:
                raise APICompatibilityError('Retrieving login page was not successfull,'
                                            f' status code: {loginResponse.status_code}')

            # Find login form on page to obtain inputs
            emailFormRegex = r'<form.+id=\"emailPasswordForm\".*action=\"(?P<formAction>[^\"]+)\"[^>]*>' \
                r'(?P<formContent>.+?(?=</form>))</form>'
            match: Optional[Match[str]] = re.search(emailFormRegex, loginResponse.text, flags=re.DOTALL)
            if match is None:
                raise APICompatibilityError('No login email form found')
            # retrieve target url from form
            target: str = match.groupdict()['formAction']

            # Find all inputs and put those in formData dictionary
            inputRegex = r'<input[\\n\\r\s][^/]*name=\"(?P<name>[^\"]+)\"([\\n\\r\s]value=\"(?P<value>[^\"]+)\")?[^/]*/>'
            formData: Dict[str, str] = {}
            for match in re.finditer(inputRegex, match.groupdict()['formContent']):
                if match.groupdict()['name']:
                    formData[match.groupdict()['name']] = match.groupdict()['value']
            if not all(x in ['_csrf', 'relayState', 'hmac', 'email'] for x in formData):
                raise APICompatibilityError('Could not find all required input fields in login page')

            # Set email to the provided username
            formData['email'] = self.username

            # build url from form action
            login2Url: str = 'https://identity.vwgroup.io' + target

            loginHeadersForm: CaseInsensitiveDict = self.DEFAULT_OPTIONS['loginHeaders']
            loginHeadersForm['Content-Type'] = 'application/x-www-form-urlencoded'

            # Post form content and retrieve credentials page
            login2Response: requests.Response = self.__session.post(login2Url, headers=loginHeadersForm, data=formData, allow_redirects=True)
            if login2Response.status_code != requests.codes['ok']:  # pylint: disable=E1101
                raise APICompatibilityError('Retrieving credentials page was not successfull,'
                                            f' status code: {login2Response.status_code}')

            # Find credentials form on page to obtain inputs
            credentialsFormRegex = r'<form.+id=\"credentialsForm\".*action=\"(?P<formAction>[^\"]+)\"[^>]*>' \
                r'(?P<formContent>.+?(?=</form>))</form>'
            match = re.search(credentialsFormRegex, login2Response.text, flags=re.DOTALL)
            if match is None:
                formErrorRegex = r'<div.+class=\".*error\">.*<span\sclass=\"message\">' \
                    r'(?P<errorMessage>.+?(?=</span>))</span>.*</div>'
                errorMatch: Optional[Match[str]] = re.search(formErrorRegex, login2Response.text, flags=re.DOTALL)
                if errorMatch is not None:
                    raise AuthentificationError(errorMatch.groupdict()['errorMessage'])

                accountNotFoundRegex = r'<div\sid=\"title\"\sclass=\"title\">.*<div class=\"sub-title\">.*<div>' \
                    r'(?P<errorMessage>.+?(?=</div>))</div>.*</div>.*</div>'
                errorMatch = re.search(accountNotFoundRegex, login2Response.text, flags=re.DOTALL)
                if errorMatch is not None:
                    errorMessage: str = re.sub('<[^<]+?>', '', errorMatch.groupdict()['errorMessage'])
                    raise AuthentificationError(errorMessage)
                raise APICompatibilityError('No credentials form found')
            # retrieve target url from form
            target = match.groupdict()['formAction']

            # Find all inputs and put those in formData dictionary
            input2Regex = r'<input[\\n\\r\s][^/]*name=\"(?P<name>[^\"]+)\"([\\n\\r\s]value=\"(?P<value>[^\"]+)\")?[^/]*/>'
            form2Data: Dict[str, str] = {}
            for match in re.finditer(input2Regex, match.groupdict()['formContent']):
                if match.groupdict()['name']:
                    form2Data[match.groupdict()['name']] = match.groupdict()['value']
            if not all(x in ['_csrf', 'relayState', 'hmac', 'email', 'password'] for x in form2Data):
                raise APICompatibilityError('Could not find all required input fields in login page')
            form2Data['password'] = self.password

            # build url from form action
            login3Url: str = 'https://identity.vwgroup.io' + target

            # Post form content and retrieve userId in forwarding Location
            login3Response: requests.Response = self.__session.post(login3Url, headers=loginHeadersForm, data=form2Data, allow_redirects=False)
            if login3Response.status_code not in (requests.codes['found'], requests.codes['see_other']):
                raise APICompatibilityError('Forwarding expected (status code 302),'
                                            f' but got status code {login3Response.status_code}')
            if 'Location' not in login3Response.headers:
                raise APICompatibilityError('No url for forwarding in response headers')

            # Parse parametes from forwarding url
            params: Dict[str, str] = dict(parse.parse_qsl(parse.urlsplit(login3Response.headers['Location']).query))

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
                raise APICompatibilityError('No user id provided')
            self.__userId = params['userId']  # pylint: disable=unused-private-member

            # Now follow the forwarding until forwarding URL starts with 'weconnect://authenticated#'
            afterLoginUrl: str = login3Response.headers['Location']
            consentURL: Optional[str] = None
            while True:
                if 'consent' in afterLoginUrl:
                    consentURL = afterLoginUrl
                afterLoginResponse = self.__session.get(
                    afterLoginUrl, headers=self.DEFAULT_OPTIONS['loginHeaders'], allow_redirects=False)

                if 'Location' not in afterLoginResponse.headers:
                    if consentURL is not None:
                        raise AuthentificationError('It seems like you need to accept the terms and conditions for the WeConnect ID service.'
                                                    f' Try to visit the URL "{consentURL}" or log into the WeConnect ID smartphone app')
                    raise APICompatibilityError('No Location for forwarding in response headers')

                afterLoginUrl = afterLoginResponse.headers['Location']

                if afterLoginUrl.startswith('weconnect://authenticated#'):
                    break

            params = dict(parse.parse_qsl(parse.urlsplit(afterLoginUrl.replace('authenticated#', 'authenticated?')).query))

        if all(key in params for key in ('token_type', 'id_token', 'expires_in')):
            self.__token = {
                'type': params['token_type'],
                'token': params['id_token'],
                'expires': datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=int(params['expires_in']))
            }
            if cast(str, self.__token['type']).casefold() == 'Bearer'.casefold():
                self.__session.auth = BearerAuth(cast(str, self.__token['token']))

        if all(key in params for key in ('state', 'id_token', 'access_token', 'code')):

            # Get Tokens
            tokenUrl: str = 'https://login.apps.emea.vwapps.io/login/v1'
            redirerctUri: str = 'weconnect://authenticated'

            body: str = json.dumps(
                {
                    'state': params['state'],
                    'id_token': params['id_token'],
                    'redirect_uri': redirerctUri,
                    'region': 'emea',
                    'access_token': params['access_token'],
                    'authorizationCode': params['code'],
                })

            tokenResponse = self.__session.post(tokenUrl, data=body, allow_redirects=False)
            data = tokenResponse.json()
            if 'idToken' in data:
                self.__token['type'] = 'Bearer'
                self.__token['token'] = data['idToken']
                self.__token['expires'] = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=3600)
                self.__session.auth = BearerAuth(cast(str, self.__token['token']))
            if 'accessToken' in data:
                self.__aToken['type'] = 'Bearer'
                self.__aToken['token'] = data['accessToken']
                self.__aToken['expires'] = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=3600)
            if 'refreshToken' in data:
                self.__rToken['type'] = 'Bearer'
                self.__rToken['token'] = data['refreshToken']
                self.__rToken['expires'] = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=3600)

            self.__refreshToken()

    def __refreshToken(self) -> None:  # noqa C901
        url: str = 'https://login.apps.emea.vwapps.io/refresh/v1'
        failed = False
        try:
            refreshResponse: requests.Response = self.__session.get(url, allow_redirects=False, auth=BearerAuth(cast(str, self.__rToken['token'])))
        except requests.exceptions.ConnectionError:
            self.notifyError(self, ErrorEventType.CONNECTION, 'connection', 'Could not refresh token due to connection problem')
            failed = True
        except requests.exceptions.ChunkedEncodingError:
            self.notifyError(self, ErrorEventType.CONNECTION, 'chunked encoding error',
                             'Could not refresh token due to connection problem with chunked encoding')
            failed = True
        except requests.exceptions.ReadTimeout:
            self.notifyError(self, ErrorEventType.TIMEOUT, 'timeout', 'Could not refresh token due to timeout')
            failed = True
        except requests.exceptions.RetryError:
            failed = True
        except requests.exceptions.HTTPError as e:
            self.notifyError(self, ErrorEventType.HTTP, e.response.status_code, 'Could not refresh token due to error')
            failed = True
        if failed:
            if self.__refreshTimer and self.__refreshTimer.is_alive():
                self.__refreshTimer.cancel()
            self.__refreshTimer = threading.Timer(60, self.__refreshToken)
            self.__refreshTimer.daemon = True
            self.__refreshTimer.start()
            LOG.info('Token could not be refreshed, will try again after 60 seconds.')
            return
        if refreshResponse.status_code == requests.codes['unauthorized']:
            self.login()
        elif refreshResponse.status_code == requests.codes['ok']:
            data: Dict[str, Any] = refreshResponse.json()

            if 'idToken' in data:
                self.__token['type'] = 'Bearer'
                self.__token['token'] = data['idToken']
                self.__token['expires'] = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=3600)
                self.__session.auth = BearerAuth(cast(str, self.__token['token']))
            else:
                LOG.error('No id token received')

            if 'accessToken' in data:
                self.__aToken['type'] = 'Bearer'
                self.__aToken['token'] = data['accessToken']
                self.__aToken['expires'] = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=3600)
                # THe access token is prefered to be used
                self.__session.auth = BearerAuth(cast(str, self.__aToken['token']))
            else:
                LOG.error('No access token received')

            if 'refreshToken' in data:
                self.__rToken['type'] = 'Bearer'
                self.__rToken['token'] = data['refreshToken']
                self.__rToken['expires'] = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=3600)
            else:
                LOG.error('No refresh token received')

            if self.__refreshTimer and self.__refreshTimer.is_alive():
                self.__refreshTimer.cancel()
            self.__refreshTimer = threading.Timer(3600 - 600, self.__refreshToken)
            self.__refreshTimer.daemon = True
            self.__refreshTimer.start()
            LOG.info('Token refreshed')
        elif refreshResponse.status_code in (requests.codes['internal_server_error'], requests.codes['service_unavailable'], requests.codes['gateway_timeout']):
            if self.__refreshTimer and self.__refreshTimer.is_alive():
                self.__refreshTimer.cancel()
            self.__refreshTimer = threading.Timer(60, self.__refreshToken)
            self.__refreshTimer.daemon = True
            self.__refreshTimer.start()
            LOG.info('Token could not be refreshed, will try again after 60 seconds.')
        else:
            raise RetrievalError(f'Status Code from WeConnect server was: {refreshResponse.status_code}')

    @property
    def vehicles(self) -> AddressableDict[str, Vehicle]:
        return self.__vehicles

    def update(self, updateCapabilities: bool = True, updatePictures: bool = True, force: bool = False) -> None:
        self.__elapsed.clear()
        self.updateVehicles(updateCapabilities=updateCapabilities, updatePictures=updatePictures, force=force)
        self.updateChargingStations(force=force)
        self.updateComplete()

    def updateVehicles(self, updateCapabilities: bool = True, updatePictures: bool = True, force: bool = False) -> None:  # noqa: C901
        data: Optional[Dict[str, Any]] = None
        cacheDate: Optional[datetime] = None
        url = 'https://mobileapi.apps.emea.vwapps.io/vehicles'
        if not force and (self.maxAge is not None and url in self.__cache):
            data, cacheDateString = self.__cache[url]
            cacheDate = datetime.fromisoformat(cacheDateString)
        if data is None or self.maxAge is None or (cacheDate is not None and cacheDate < (datetime.utcnow() - timedelta(seconds=self.maxAge))):
            try:
                vehiclesResponse: requests.Response = self.__session.get(url, allow_redirects=True)
                self.recordElapsed(vehiclesResponse.elapsed)
            except requests.exceptions.ConnectionError as connectionError:
                self.notifyError(self, ErrorEventType.CONNECTION, 'connection', 'Could not fetch vehicles due to connection problem')
                raise RetrievalError from connectionError
            except requests.exceptions.ChunkedEncodingError as chunkedEncodingError:
                self.notifyError(self, ErrorEventType.CONNECTION, 'chunked encoding error',
                                 'Could not refresh token due to connection problem with chunked encoding')
                raise RetrievalError from chunkedEncodingError
            except requests.exceptions.ReadTimeout as timeoutError:
                self.notifyError(self, ErrorEventType.TIMEOUT, 'timeout', 'Could not fetch vehicles due to timeout')
                raise RetrievalError from timeoutError
            except requests.exceptions.RetryError as retryError:
                raise RetrievalError from retryError
            if vehiclesResponse.status_code == requests.codes['ok']:
                data = vehiclesResponse.json()
            elif vehiclesResponse.status_code == requests.codes['unauthorized']:
                LOG.info('Server asks for new authorization')
                self.login()
                try:
                    vehiclesResponse = self.__session.get(url, allow_redirects=False)
                    self.recordElapsed(vehiclesResponse.elapsed)
                except requests.exceptions.ConnectionError as connectionError:
                    self.notifyError(self, ErrorEventType.CONNECTION, 'connection', 'Could not fetch vehicles due to connection problem')
                    raise RetrievalError from connectionError
                except requests.exceptions.ChunkedEncodingError as chunkedEncodingError:
                    self.notifyError(self, ErrorEventType.CONNECTION, 'chunked encoding error',
                                     'Could not refresh token due to connection problem with chunked encoding')
                    raise RetrievalError from chunkedEncodingError
                except requests.exceptions.ReadTimeout as timeoutError:
                    self.notifyError(self, ErrorEventType.TIMEOUT, 'timeout', 'Could not fetch vehicles due to timeout')
                    raise RetrievalError from timeoutError
                except requests.exceptions.RetryError as retryError:
                    raise RetrievalError from retryError
                if vehiclesResponse.status_code == requests.codes['ok']:
                    data = vehiclesResponse.json()
                else:
                    self.notifyError(self, ErrorEventType.HTTP, str(vehiclesResponse.status_code), 'Could not fetch vehicles due to server error')
                    raise RetrievalError('Could not retrieve data even after re-authorization.'
                                         f' Status Code was: {vehiclesResponse.status_code}')
            else:
                self.notifyError(self, ErrorEventType.HTTP, str(vehiclesResponse.status_code), 'Could not fetch vehicles due to server error')
                raise RetrievalError(f'Status Code from WeConnect server was: {vehiclesResponse.status_code}')
        if data is not None:
            if 'data' in data and data['data']:
                vins: List[str] = []
                for vehicleDict in data['data']:
                    if 'vin' not in vehicleDict:
                        break
                    vin: str = vehicleDict['vin']
                    vins.append(vin)
                    try:
                        if vin not in self.__vehicles:
                            vehicle = Vehicle(weConnect=self, vin=vin, parent=self.__vehicles, fromDict=vehicleDict,
                                              fixAPI=self.fixAPI, updateCapabilities=updateCapabilities, updatePictures=updatePictures)
                            self.__vehicles[vin] = vehicle
                        else:
                            self.__vehicles[vin].update(fromDict=vehicleDict, updateCapabilities=updateCapabilities, updatePictures=updatePictures)
                    except RetrievalError as retrievalError:
                        LOG.error('Failed to retrieve data for VIN %s: %s', vin, retrievalError)
                # delete those vins that are not anymore available
                for vin in [vin for vin in self.__vehicles if vin not in vins]:
                    del self.__vehicles[vin]

                self.__cache[url] = (data, str(datetime.utcnow()))

    def setChargingStationSearchParameters(self, latitude: float, longitude: float, searchRadius: Optional[int] = None, market: Optional[str] = None,
                                           useLocale: Optional[str] = locale.getlocale()[0]) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.searchRadius = searchRadius
        self.market = market
        self.useLocale = useLocale

    def getChargingStations(self, latitude, longitude, searchRadius=None, market=None, useLocale=None,  # noqa: C901
                            force=False) -> AddressableDict[str, ChargingStation]:
        chargingStationMap: AddressableDict[str, ChargingStation] = AddressableDict(localAddress='', parent=None)
        data: Optional[Dict[str, Any]] = None
        cacheDate: Optional[datetime] = None
        url: str = f'https://mobileapi.apps.emea.vwapps.io/charging-stations/v2?latitude={latitude}&longitude={longitude}'
        if market is not None:
            url += f'&market={market}'
        if useLocale is not None:
            url += f'&locale={useLocale}'
        if searchRadius is not None:
            url += f'&searchRadius={searchRadius}'
        if self.__userId is not None:
            url += f'&userId={self.__userId}'
        if not force and (self.maxAge is not None and url in self.__cache):
            data, cacheDateString = self.__cache[url]
            cacheDate = datetime.fromisoformat(cacheDateString)
        if data is None or self.maxAge is None or (cacheDate is not None and cacheDate < (datetime.utcnow() - timedelta(seconds=self.maxAge))):
            try:
                stationsResponse: requests.Response = self.__session.get(url, allow_redirects=True)
                self.recordElapsed(stationsResponse.elapsed)
            except requests.exceptions.ConnectionError as connectionError:
                self.notifyError(self, ErrorEventType.CONNECTION, 'connection', 'Could not fetch charging stations due to connection problem')
                raise RetrievalError from connectionError
            except requests.exceptions.ChunkedEncodingError as chunkedEncodingError:
                self.notifyError(self, ErrorEventType.CONNECTION, 'chunked encoding error',
                                 'Could not refresh token due to connection problem with chunked encoding')
                raise RetrievalError from chunkedEncodingError
            except requests.exceptions.ReadTimeout as timeoutError:
                self.notifyError(self, ErrorEventType.TIMEOUT, 'timeout', 'Could not fetch charging stations due to timeout')
                raise RetrievalError from timeoutError
            except requests.exceptions.RetryError as retryError:
                raise RetrievalError from retryError
            if stationsResponse.status_code == requests.codes['ok']:
                data = stationsResponse.json()
            elif stationsResponse.status_code == requests.codes['unauthorized']:
                LOG.info('Server asks for new authorization')
                self.login()
                try:
                    stationsResponse = self.__session.get(url, allow_redirects=False)
                    self.recordElapsed(stationsResponse.elapsed)
                except requests.exceptions.ConnectionError as connectionError:
                    self.notifyError(self, ErrorEventType.CONNECTION, 'connection', 'Could not fetch charging stations due to connection problem')
                    raise RetrievalError from connectionError
                except requests.exceptions.ChunkedEncodingError as chunkedEncodingError:
                    self.notifyError(self, ErrorEventType.CONNECTION, 'chunked encoding error',
                                     'Could not refresh token due to connection problem with chunked encoding')
                    raise RetrievalError from chunkedEncodingError
                except requests.exceptions.ReadTimeout as timeoutError:
                    self.notifyError(self, ErrorEventType.TIMEOUT, 'timeout', 'Could not fetch charging stations due to timeout')
                    raise RetrievalError from timeoutError
                except requests.exceptions.RetryError as retryError:
                    raise RetrievalError from retryError
                if stationsResponse.status_code == requests.codes['ok']:
                    data = stationsResponse.json()
                else:
                    self.notifyError(self, ErrorEventType.HTTP, str(stationsResponse.status_code),
                                     'Could not fetch charging stations due to server error')
                    raise RetrievalError('Could not retrieve data even after re-authorization.'
                                         f' Status Code was: {stationsResponse.status_code}')
            else:
                self.notifyError(self, ErrorEventType.HTTP, str(stationsResponse.status_code),
                                 'Could not fetch charging stations due to server error')
                raise RetrievalError(f'Status Code from WeConnect server was: {stationsResponse.status_code}')
        if data is not None:
            if 'chargingStations' in data and data['chargingStations']:
                for stationDict in data['chargingStations']:
                    if 'id' not in stationDict:
                        break
                    stationId: str = stationDict['id']
                    station: ChargingStation = ChargingStation(weConnect=self, stationId=stationId, parent=chargingStationMap, fromDict=stationDict,
                                                               fixAPI=self.fixAPI)
                    chargingStationMap[stationId] = station

                self.__cache[url] = (data, str(datetime.utcnow()))
        return chargingStationMap

    def updateChargingStations(self, force: bool = False) -> None:  # noqa: C901 # pylint: disable=too-many-branches
        if self.latitude is not None and self.longitude is not None:
            data: Optional[Dict[str, Any]] = None
            cacheDate: Optional[datetime] = None
            url: str = f'https://mobileapi.apps.emea.vwapps.io/charging-stations/v2?latitude={self.latitude}&longitude={self.longitude}'
            if self.market is not None:
                url += f'&market={self.market}'
            if self.useLocale is not None:
                url += f'&locale={self.useLocale}'
            if self.searchRadius is not None:
                url += f'&searchRadius={self.searchRadius}'
            if self.__userId is not None:
                url += f'&userId={self.__userId}'
            if not force and (self.maxAge is not None and url in self.__cache):
                data, cacheDateString = self.__cache[url]
                cacheDate = datetime.fromisoformat(cacheDateString)
            if data is None or self.maxAge is None or (cacheDate is not None and cacheDate < (datetime.utcnow() - timedelta(seconds=self.maxAge))):
                try:
                    stationsResponse: requests.Response = self.__session.get(url, allow_redirects=True)
                    self.recordElapsed(stationsResponse.elapsed)
                except requests.exceptions.ConnectionError as connectionError:
                    self.notifyError(self, ErrorEventType.CONNECTION, 'connection', 'Could not fetch charging stations due to connection problem')
                    raise RetrievalError from connectionError
                except requests.exceptions.ChunkedEncodingError as chunkedEncodingError:
                    self.notifyError(self, ErrorEventType.CONNECTION, 'chunked encoding error',
                                     'Could not refresh token due to connection problem with chunked encoding')
                    raise RetrievalError from chunkedEncodingError
                except requests.exceptions.ReadTimeout as timeoutError:
                    self.notifyError(self, ErrorEventType.TIMEOUT, 'timeout', 'Could not fetch charging stations due to timeout')
                    raise RetrievalError from timeoutError
                except requests.exceptions.RetryError as retryError:
                    raise RetrievalError from retryError
                if stationsResponse.status_code == requests.codes['ok']:
                    data = stationsResponse.json()
                elif stationsResponse.status_code == requests.codes['unauthorized']:
                    LOG.info('Server asks for new authorization')
                    self.login()
                    try:
                        stationsResponse = self.__session.get(url, allow_redirects=False)
                        self.recordElapsed(stationsResponse.elapsed)
                    except requests.exceptions.ConnectionError as connectionError:
                        self.notifyError(self, ErrorEventType.CONNECTION, 'connection', 'Could not fetch charging station due to connection problem')
                        raise RetrievalError from connectionError
                    except requests.exceptions.ChunkedEncodingError as chunkedEncodingError:
                        self.notifyError(self, ErrorEventType.CONNECTION, 'chunked encoding error',
                                         'Could not refresh token due to connection problem with chunked encoding')
                        raise RetrievalError from chunkedEncodingError
                    except requests.exceptions.ReadTimeout as timeoutError:
                        self.notifyError(self, ErrorEventType.TIMEOUT, 'timeout', 'Could not fetch charging station due to timeout')
                        raise RetrievalError from timeoutError
                    except requests.exceptions.RetryError as retryError:
                        raise RetrievalError from retryError
                    if stationsResponse.status_code == requests.codes['ok']:
                        data = stationsResponse.json()
                    else:
                        self.notifyError(self, ErrorEventType.HTTP, str(stationsResponse.status_code),
                                         'Could not fetch charging stations due to server error')
                        raise RetrievalError('Could not retrieve data even after re-authorization.'
                                             f' Status Code was: {stationsResponse.status_code}')
                else:
                    self.notifyError(self, ErrorEventType.HTTP, str(stationsResponse.status_code),
                                     'Could not fetch charging stations due to server error')
                    raise RetrievalError(f'Status Code from WeConnect server was: {stationsResponse.status_code}')
            if data is not None:
                if 'chargingStations' in data and data['chargingStations']:
                    ids: List[str] = []
                    for stationDict in data['chargingStations']:
                        if 'id' not in stationDict:
                            break
                        stationId: str = stationDict['id']
                        ids.append(stationId)
                        if stationId not in self.__stations:
                            station: ChargingStation = ChargingStation(weConnect=self, stationId=stationId, parent=self.__stations, fromDict=stationDict,
                                                                       fixAPI=self.fixAPI)
                            self.__stations[stationId] = station
                        else:
                            self.__stations[stationId].update(fromDict=stationDict)
                    # delete those vins that are not anymore available
                    for stationId in [stationId for stationId in ids if stationId not in self.__stations]:
                        del self.__stations[stationId]

                    self.__cache[url] = (data, str(datetime.utcnow()))

    def getLeafChildren(self) -> List[AddressableLeaf]:
        return [children for vehicle in self.__vehicles.values() for children in vehicle.getLeafChildren()] \
            + [children for station in self.__stations.values() for children in station.getLeafChildren()]

    def __str__(self) -> str:
        returnString: str = ''
        for vin, vehicle in self.__vehicles.items():
            returnString += f'Vehicle: {vin}\n{vehicle}\n'
        for stationId, station in sorted(self.__stations.items(), key=lambda x: x[1].distance.value, reverse=False):
            returnString += f'Charging Station: {stationId}\n{station}\n'
        return returnString

    def addErrorObserver(self, observer: Callable, errortype: ErrorEventType) -> None:
        self.__errorObservers.add((observer, errortype))
        LOG.debug('%s: Error event observer added for type: %s', self.getGlobalAddress(), errortype)

    def removeErrorObserver(self, observer: Callable, errortype: Optional[ErrorEventType] = None) -> None:
        self.__errorObservers = filter(lambda observerEntry: observerEntry[0] == observer
                                       or (errortype is not None and observerEntry[1] == errortype), self.__errorObservers)

    def getErrorObservers(self, errortype) -> List[Any]:
        return [observerEntry[0] for observerEntry in self.getErrorObserverEntries(errortype)]

    def getErrorObserverEntries(self, errortype: ErrorEventType) -> List[Any]:
        observers: Set[Tuple[Callable, ErrorEventType]] = set()
        for observerEntry in self.__errorObservers:
            observer, observertype = observerEntry
            del observer
            if errortype & observertype:
                observers.add(observerEntry)
        return observers

    def notifyError(self, element, errortype: ErrorEventType, detail: string, message: string = None) -> None:
        observers: List[Callable] = self.getErrorObservers(errortype)
        for observer in observers:
            observer(element=element, errortype=errortype, detail=detail, message=message)
        LOG.debug('%s: Notify called for errors with type: %s for %d observers', self.getGlobalAddress(), errortype, len(observers))

    def recordElapsed(self, elapsed: timedelta) -> None:
        self.__elapsed.append(elapsed)

    def getMinElapsed(self) -> timedelta:
        if len(self.__elapsed) == 0:
            return None
        return min(self.__elapsed)

    def getMaxElapsed(self) -> timedelta:
        if len(self.__elapsed) == 0:
            return None
        return max(self.__elapsed)

    def getAvgElapsed(self) -> timedelta:
        if len(self.__elapsed) == 0:
            return None
        return sum(self.__elapsed, timedelta()) / len(self.__elapsed)

    def getTotalElapsed(self) -> timedelta:
        if len(self.__elapsed) == 0:
            return None
        return sum(self.__elapsed, timedelta())
