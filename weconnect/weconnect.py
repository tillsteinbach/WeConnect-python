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

from weconnect.elements.vehicle import Vehicle
from weconnect.elements.charging_station import ChargingStation
from weconnect.addressable import AddressableObject, AddressableDict
from weconnect.errors import APICompatibilityError, AuthentificationError, RetrievalError

LOG = logging.getLogger("weconnect")


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)


class WeConnect(AddressableObject):  # pylint: disable=too-many-instance-attributes
    DEFAULT_OPTIONS = {
        "headers": {
            'accept': '*/*',
            'content-type': 'application/json',
            'content-version': '1',
            'x-newrelic-id': 'VgAEWV9QDRAEXFlRAAYPUA==',
            'user-agent': 'WeConnect/5 CFNetwork/1206 Darwin/20.1.0',
            'accept-language': 'de-de',
        },
        "loginHeaders": {
            'user-agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 '
                          'Chrome/74.0.3729.185 Mobile Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                      'application/signed-exchange;v=b3',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'gzip, deflate',
            'x-requested-with': 'de.volkswagen.carnet.eu.eremote',
            'upgrade-insecure-requests': '1',
        },
        "refreshBeforeExpires": 30
    }

    def __init__(  # noqa: C901 # pylint: disable=too-many-arguments
        self,
        username,
        password,
        tokenfile=None,
        updateAfterLogin=True,
        loginOnInit=True,
        refreshTokens=True,
        fixAPI=True,
        maxAge=None,
        updateCapabilities=True,
        updatePictures=True
    ):
        super().__init__(localAddress='', parent=None)
        self.username = username
        self.password = password
        self.__token = {'type': None, 'token': None, 'expires': None}
        self.__aToken = {'type': None, 'token': None, 'expires': None}
        self.__rToken = {'type': None, 'token': None, 'expires': None}
        self.__userId = None  # pylint: disable=unused-private-member
        self.__session = requests.Session()
        self.__refreshTimer = None
        self.__vehicles = AddressableDict(localAddress='vehicles', parent=self)
        self.__stations = AddressableDict(localAddress='chargingStations', parent=self)
        self.__cache = dict()
        self.fixAPI = fixAPI
        self.maxAge = maxAge
        self.latitude = None
        self.longitude = None
        self.searchRadius = None
        self.market = None
        self.useLocale = locale.getlocale()[0]

        self.__session.headers = self.DEFAULT_OPTIONS['headers']

        self.tokenfile = tokenfile
        if self.tokenfile:
            try:
                with open(self.tokenfile, 'r') as file:
                    tokens = requests.utils.cookiejar_from_dict(json.load(file))

                if 'idToken' in tokens and all(key in tokens['idToken'] for key in ('type', 'token', 'expires')):
                    self.__token['type'] = tokens['idToken']['type']
                    self.__token['token'] = tokens['idToken']['token']
                    self.__token['expires'] = datetime.fromisoformat(tokens['idToken']['expires'])
                    self.__session.auth = BearerAuth(self.__token['token'])
                else:
                    LOG.info('Could not use token from file %s (does not contain a token)', self.tokenfile)

                if 'accessToken' in tokens and all(key in tokens['accessToken'] for key in ('type', 'token', 'expires')):
                    self.__aToken['type'] = tokens['accessToken']['type']
                    self.__aToken['token'] = tokens['accessToken']['token']
                    self.__aToken['expires'] = datetime.fromisoformat(tokens['accessToken']['expires'])
                    self.__session.auth = BearerAuth(self.__aToken['token'])
                else:
                    LOG.info('Could not use token from file %s (does not contain a token)', self.tokenfile)

                if 'refreshToken' in tokens and all(key in tokens['refreshToken']
                                                    for key in ('type', 'token', 'expires')):
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
            if self.__token['expires'] is None or self.__token['expires'] <= \
                    datetime.utcnow().replace(tzinfo=timezone.utc):
                self.login()
            else:
                LOG.info('Login not necessary, token still valid')

        if updateAfterLogin:
            self.update(updateCapabilities=updateCapabilities, updatePictures=updatePictures)

    @property
    def session(self):
        return self.__session

    @property
    def cache(self):
        return self.__cache

    def persistTokens(self):
        if self.tokenfile:
            try:
                with open(self.tokenfile, 'w') as file:
                    json.dump({'idToken': self.__token, 'refreshToken': self.__rToken, 'accessToken': self.__aToken}, file, cls=DateTimeEncoder)
                LOG.info('Writing tokenfile %s', self.tokenfile)
            except ValueError as err:  # pragma: no cover
                LOG.info('Could not write tokenfile %s (%s)', self.tokenfile, err)

    def persistCacheAsJson(self, filename):
        with open(filename, 'w') as file:
            json.dump(self.__cache, file, cls=DateTimeEncoder)
        LOG.info('Writing cachefile %s', filename)

    def fillCacheFromJson(self, filename, maxAge):
        self.maxAge = maxAge
        with open(filename, 'r') as file:
            self.__cache = json.load(file)
        LOG.info('Reading cachefile %s', filename)

    def fillCacheFromJsonString(self, jsonString, maxAge):
        self.maxAge = maxAge
        self.__cache = json.loads(jsonString)
        LOG.info('Reading cache from string')

    def clearCache(self, maxAge):
        self.maxAge = maxAge
        self.__cache.clear()
        LOG.info('Clearing cache')

    def login(self):  # noqa: C901 # pylint: disable=R0914, R0912, too-many-statements
        # Try to access page to be redirected to login form
        tryLoginUrl = f'https://login.apps.emea.vwapps.io/authorize?nonce=' \
            f'{"".join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=16))}' \
            '&redirect_uri=weconnect://authenticated'

        tryLoginResponse = self.__session.get(tryLoginUrl, allow_redirects=False)
        if tryLoginResponse.status_code != requests.codes['see_other']:
            raise APICompatibilityError('Forwarding to login page expected (status code 303),'
                                        f' but got status code {tryLoginResponse.status_code}')
        if 'Location' not in tryLoginResponse.headers:
            raise APICompatibilityError('No url for forwarding in response headers')
        # Login url is in response headers when response has status code see_others (303)
        loginUrl = tryLoginResponse.headers['Location']

        # Retrieve login page
        loginResponse = self.__session.get(loginUrl, headers=self.DEFAULT_OPTIONS['loginHeaders'], allow_redirects=True)
        if loginResponse.status_code != requests.codes['ok']:
            raise APICompatibilityError('Retrieving login page was not successfull,'
                                        f' status code: {loginResponse.status_code}')

        # Find login form on page to obtain inputs
        formRegex = r'<form.+id=\"emailPasswordForm\".*action=\"(?P<formAction>[^\"]+)\"[^>]*>' \
            r'(?P<formContent>.+?(?=</form>))</form>'
        match = re.search(formRegex, loginResponse.text, flags=re.DOTALL)
        if match is None:
            raise APICompatibilityError('No login email form found')
        # retrieve target url from form
        target = match.groupdict()['formAction']

        # Find all inputs and put those in formData dictionary
        inputRegex = r'<input[\\n\\r\s][^/]*name=\"(?P<name>[^\"]+)\"([\\n\\r\s]value=\"(?P<value>[^\"]+)\")?[^/]*/>'
        formData = dict()
        for match in re.finditer(inputRegex, match.groupdict()['formContent']):
            if match.groupdict()['name']:
                formData[match.groupdict()['name']] = match.groupdict()['value']
        if not all(x in ['_csrf', 'relayState', 'hmac', 'email'] for x in formData):
            raise APICompatibilityError('Could not find all required input fields in login page')

        # Set email to the provided username
        formData['email'] = self.username

        # build url from form action
        login2Url = 'https://identity.vwgroup.io' + target

        loginHeadersForm = self.DEFAULT_OPTIONS['loginHeaders']
        loginHeadersForm['Content-Type'] = 'application/x-www-form-urlencoded'

        # Post form content and retrieve credentials page
        login2Response = self.__session.post(login2Url, headers=loginHeadersForm, data=formData, allow_redirects=True)
        if login2Response.status_code != requests.codes['ok']:  # pylint: disable=E1101
            raise APICompatibilityError('Retrieving credentials page was not successfull,'
                                        f' status code: {login2Response.status_code}')

        # Find credentials form on page to obtain inputs
        formRegex = r'<form.+id=\"credentialsForm\".*action=\"(?P<formAction>[^\"]+)\"[^>]*>' \
            r'(?P<formContent>.+?(?=</form>))</form>'
        match = re.search(formRegex, login2Response.text, flags=re.DOTALL)
        if match is None:
            formErrorRegex = r'<div.+class=\".*error\">.*<span\sclass=\"message\">' \
                r'(?P<errorMessage>.+?(?=</span>))</span>.*</div>'
            errorMatch = re.search(formErrorRegex, login2Response.text, flags=re.DOTALL)
            if errorMatch is not None:
                raise AuthentificationError(errorMatch.groupdict()['errorMessage'])

            accountNotFoundRegex = r'<div\sid=\"title\"\sclass=\"title\">.*<div class=\"sub-title\">.*<div>' \
                r'(?P<errorMessage>.+?(?=</div>))</div>.*</div>.*</div>'
            errorMatch = re.search(accountNotFoundRegex, login2Response.text, flags=re.DOTALL)
            if errorMatch is not None:
                errorMessage = re.sub('<[^<]+?>', '', errorMatch.groupdict()['errorMessage'])
                raise AuthentificationError(errorMessage)
            raise APICompatibilityError('No credentials form found')
        # retrieve target url from form
        target = match.groupdict()['formAction']

        # Find all inputs and put those in formData dictionary
        inputRegex = r'<input[\\n\\r\s][^/]*name=\"(?P<name>[^\"]+)\"([\\n\\r\s]value=\"(?P<value>[^\"]+)\")?[^/]*/>'
        form2Data = dict()
        for match in re.finditer(inputRegex, match.groupdict()['formContent']):
            if match.groupdict()['name']:
                form2Data[match.groupdict()['name']] = match.groupdict()['value']
        if not all(x in ['_csrf', 'relayState', 'hmac', 'email', 'password'] for x in form2Data):
            raise APICompatibilityError('Could not find all required input fields in login page')
        form2Data['password'] = self.password

        # build url from form action
        login3Url = 'https://identity.vwgroup.io' + target

        # Post form content and retrieve userId in forwarding Location
        login3Response = self.__session.post(login3Url, headers=loginHeadersForm, data=form2Data, allow_redirects=False)
        if login3Response.status_code != requests.codes['found'] \
                and login3Response.status_code != requests.codes['see_other']:
            raise APICompatibilityError('Forwarding expected (status code 302),'
                                        f' but got status code {login3Response.status_code}')
        if 'Location' not in login3Response.headers:
            raise APICompatibilityError('No url for forwarding in response headers')

        # Parse parametes from forwarding url
        params = dict(parse.parse_qsl(parse.urlsplit(login3Response.headers['Location']).query))

        # Check if error
        if 'error' in params and params['error']:
            errorMessages = {
                'login.errors.password_invalid': 'Password is invalid',
                'login.error.throttled': 'Login throttled, probably too many wrong logins. You have to wait some'
                                         ' minutes until a new login attempt is possible'
            }
            if params['error'] in errorMessages.keys():
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
        afterLoginUrl = login3Response.headers['Location']
        consentURL = None
        while True:
            if 'consent' in afterLoginUrl:
                consentURL = afterLoginUrl
            afterLoginResponse = self.__session.get(
                afterLoginUrl, headers=self.DEFAULT_OPTIONS['loginHeaders'], allow_redirects=False)

            if 'Location' not in afterLoginResponse.headers:
                if consentURL is not None:
                    raise AuthentificationError('It seems like you need to accept the terms and conditions for the WeConnect ID service.'
                                                ' Try to visit the URL "{consentURL}" or log into the WeConnect ID smartphone app')
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
            if self.__token['type'].casefold() == 'Bearer'.casefold():
                self.__session.auth = BearerAuth(self.__token['token'])

        if all(key in params for key in ('state', 'id_token', 'access_token', 'code')):

            # Get Tokens
            tokenUrl = 'https://login.apps.emea.vwapps.io/login/v1'
            redirerctUri = 'weconnect://authenticated'

            body = json.dumps(
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
                self.__session.auth = BearerAuth(self.__token['token'])
            if 'accessToken' in data:
                self.__aToken['type'] = 'Bearer'
                self.__aToken['token'] = data['accessToken']
                self.__aToken['expires'] = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=3600)
            if 'refreshToken' in data:
                self.__rToken['type'] = 'Bearer'
                self.__rToken['token'] = data['refreshToken']
                self.__rToken['expires'] = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=3600)

            self.__refreshToken()

    def __refreshToken(self):
        url = 'https://login.apps.emea.vwapps.io/refresh/v1'

        refreshResponse = self.__session.get(url, allow_redirects=False, auth=BearerAuth(self.__rToken['token']))
        if refreshResponse.status_code == requests.codes['unauthorized']:
            self.login()
        elif refreshResponse.status_code == requests.codes['ok']:
            data = refreshResponse.json()

            if 'idToken' in data:
                self.__token['type'] = 'Bearer'
                self.__token['token'] = data['idToken']
                self.__token['expires'] = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=3600)
                self.__session.auth = BearerAuth(self.__token['token'])
            else:
                LOG.error('No id token received')

            if 'accessToken' in data:
                self.__aToken['type'] = 'Bearer'
                self.__aToken['token'] = data['accessToken']
                self.__aToken['expires'] = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=3600)
                # THe access token is prefered to be used
                self.__session.auth = BearerAuth(self.__aToken['token'])
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
        elif refreshResponse.status_code == requests.codes['internal_server_error'] \
                or refreshResponse.status_code == requests.codes['service_unavailable'] \
                or refreshResponse.status_code == requests.codes['gateway_timeout']:
            if self.__refreshTimer and self.__refreshTimer.is_alive():
                self.__refreshTimer.cancel()
            self.__refreshTimer = threading.Timer(60, self.__refreshToken)
            self.__refreshTimer.daemon = True
            self.__refreshTimer.start()
            LOG.info('Token could not be refreshed, will try again after 60 seconds.')
        else:
            raise RetrievalError(f'Status Code from WeConnect server was: {refreshResponse.status_code}')

    @property
    def vehicles(self):
        return self.__vehicles

    def update(self, updateCapabilities=True, updatePictures=True, force=False):
        self.updateVehicles(updateCapabilities=updateCapabilities, updatePictures=updatePictures, force=force)
        self.updateChargingStations(force=force)
        self.updateComplete()

    def updateVehicles(self, updateCapabilities=True, updatePictures=True, force=False):  # noqa: C901
        data = None
        cacheDate = None
        url = 'https://mobileapi.apps.emea.vwapps.io/vehicles'
        if force or (self.maxAge is not None and url in self.__cache):
            data, cacheDateString = self.__cache[url]
            cacheDate = datetime.fromisoformat(cacheDateString)
        if data is None or self.maxAge is None or (cacheDate is not None and cacheDate < (datetime.utcnow() - timedelta(seconds=self.maxAge))):
            try:
                vehiclesResponse = self.__session.get(url, allow_redirects=True)
            except requests.exceptions.ConnectionError as conenctionError:
                raise RetrievalError from conenctionError
            if vehiclesResponse.status_code == requests.codes['ok']:
                data = vehiclesResponse.json()
            elif vehiclesResponse.status_code == requests.codes['unauthorized']:
                LOG.info('Server asks for new authorization')
                self.login()
                vehiclesResponse = self.__session.get(url, allow_redirects=False)
                if vehiclesResponse.status_code == requests.codes['ok']:
                    data = vehiclesResponse.json()
                else:
                    raise RetrievalError('Could not retrieve data even after re-authorization.'
                                         f' Status Code was: {vehiclesResponse.status_code}')
            else:
                raise RetrievalError(f'Status Code from WeConnect server was: {vehiclesResponse.status_code}')
        if data is not None:
            if 'data' in data and data['data']:
                vins = list()
                for vehicleDict in data['data']:
                    if 'vin' not in vehicleDict:
                        break
                    vin = vehicleDict['vin']
                    vins.append(vin)
                    if vin not in self.__vehicles:
                        vehicle = Vehicle(weConnect=self, vin=vin, parent=self.__vehicles, fromDict=vehicleDict,
                                          fixAPI=self.fixAPI, updateCapabilities=updateCapabilities, updatePictures=updatePictures)
                        self.__vehicles[vin] = vehicle
                    else:
                        self.__vehicles[vin].update(fromDict=vehicleDict, updateCapabilities=updateCapabilities, updatePictures=updatePictures)
                # delete those vins that are not anymore available
                for vin in [vin for vin in vins if vin not in self.__vehicles]:
                    del self.__vehicles[vin]

                self.__cache[url] = (data, str(datetime.utcnow()))

    def setChargingStationSearchParameters(self, latitude, longitude, searchRadius=None, market=None, useLocale=locale.getlocale()[0]):
        self.latitude = latitude
        self.longitude = longitude
        self.searchRadius = searchRadius
        self.market = market
        self.useLocale = useLocale

    def updateChargingStations(self, force=False):  # noqa: C901
        if self.latitude is not None and self.longitude is not None:
            data = None
            cacheDate = None
            url = f'https://mobileapi.apps.emea.vwapps.io/charging-stations/v2?latitude={self.latitude}&longitude={self.longitude}'
            if self.market is not None:
                url += f'&market={self.market}'
            if self.useLocale is not None:
                url += f'&locale={self.useLocale}'
            if self.searchRadius is not None:
                url += f'&searchRadius={self.searchRadius}'
            if self.__userId is not None:
                url += f'&userId={self.__userId}'
            if force or (self.maxAge is not None and url in self.__cache):
                data, cacheDateString = self.__cache[url]
                cacheDate = datetime.fromisoformat(cacheDateString)
            if data is None or self.maxAge is None or (cacheDate is not None and cacheDate < (datetime.utcnow() - timedelta(seconds=self.maxAge))):
                try:
                    stationsResponse = self.__session.get(url, allow_redirects=True)
                except requests.exceptions.ConnectionError as conenctionError:
                    raise RetrievalError from conenctionError
                if stationsResponse.status_code == requests.codes['ok']:
                    data = stationsResponse.json()
                elif stationsResponse.status_code == requests.codes['unauthorized']:
                    LOG.info('Server asks for new authorization')
                    self.login()
                    stationsResponse = self.__session.get(url, allow_redirects=False)
                    if stationsResponse.status_code == requests.codes['ok']:
                        data = stationsResponse.json()
                    else:
                        raise RetrievalError('Could not retrieve data even after re-authorization.'
                                             f' Status Code was: {stationsResponse.status_code}')
                else:
                    raise RetrievalError(f'Status Code from WeConnect server was: {stationsResponse.status_code}')
            if data is not None:
                if 'chargingStations' in data and data['chargingStations']:
                    ids = list()
                    for stationDict in data['chargingStations']:
                        if 'id' not in stationDict:
                            break
                        stationId = stationDict['id']
                        ids.append(stationId)
                        if stationId not in self.__stations:
                            station = ChargingStation(weConnect=self, stationId=stationId, parent=self.__stations, fromDict=stationDict,
                                                      fixAPI=self.fixAPI)
                            self.__stations[stationId] = station
                        else:
                            self.__stations[stationId].update(fromDict=stationDict)
                    # delete those vins that are not anymore available
                    for stationId in [stationId for stationId in ids if stationId not in self.__stations]:
                        del self.__stations[stationId]

                    self.__cache[url] = (data, str(datetime.utcnow()))

    def getLeafChildren(self):
        return [children for vehicle in self.__vehicles.values() for children in vehicle.getLeafChildren()] \
            + [children for station in self.__stations.values() for children in station.getLeafChildren()]

    def __str__(self):
        returnString = ''
        for vin, vehicle in self.__vehicles.items():
            returnString += f'Vehicle: {vin}\n{vehicle}\n'
        for stationId, station in sorted(self.__stations.items(), key=lambda x: x[1].distance.value, reverse=False):
            returnString += f'Charging Station: {stationId}\n{station}\n'
        return returnString
