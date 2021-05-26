import string
import random
import re
import logging
import threading
import json
from datetime import datetime, timedelta
from urllib import parse

import requests

from .elements import Vehicle
from .addressable import AddressableObject, AddressableDict


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


class WeConnect(AddressableObject):
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

    def __init__(
        self,
        username,
        password,
        tokenfile=None,
        updateAfterLogin=True
    ):
        super().__init__(localAddress='', parent=None)
        self.username = username
        self.password = password
        self.__token = {'type': None, 'token': None, 'expires': None}
        self.__aToken = {'type': None, 'token': None, 'expires': None}
        self.__rToken = {'type': None, 'token': None, 'expires': None}
        self.__userId = None
        self.__session = requests.Session()
        self.__refreshTimer = None
        self.__vehicles = AddressableDict(localAddress='vehicles', parent=self)

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
                    logging.info('Could not use token from file %s (does not contain a token)', self.tokenfile)

                if 'refreshToken' in tokens and all(key in tokens['refreshToken']
                                                    for key in ('type', 'token', 'expires')):
                    self.__rToken['type'] = tokens['refreshToken']['type']
                    self.__rToken['token'] = tokens['refreshToken']['token']
                    self.__rToken['expires'] = datetime.fromisoformat(tokens['refreshToken']['expires'])
                else:
                    logging.info('Could not use refreshToken from file %s (does not contain a token)', self.tokenfile)

                # Refresh tokens once
                self.__refreshToken()

            except json.JSONDecodeError as err:
                logging.info('Could not use token from file %s (%s)', tokenfile, err.msg)
            except FileNotFoundError as err:
                logging.info('Could not use token from file %s (%s)', tokenfile, err)

        if self.__token['expires'] is None or self.__token['expires'] <= datetime.now():
            self.__login()
        else:
            logging.info('Login not necessary, token still valid')
        if updateAfterLogin:
            self.update()

    def __del__(self):
        if self.tokenfile:
            try:
                with open(self.tokenfile, 'w') as file:
                    json.dump({'idToken': self.__token, 'refreshToken': self.__rToken}, file, cls=DateTimeEncoder)
                logging.info('Writing tookenfile %s', self.tokenfile)
            except ValueError as err:  # pragma: no cover
                logging.info('Could not write tokenfile %s (%s)', self.tokenfile, err)

    def __login(self):  # noqa: C901
        tryLoginUrl = f'https://login.apps.emea.vwapps.io/authorize?nonce=' \
            f'{"".join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=16))}' \
            '&redirect_uri=weconnect://authenticated'

        tryLoginResponse = self.__session.get(tryLoginUrl, allow_redirects=False)
        loginUrl = tryLoginResponse.headers['Location']

        loginResponse = self.__session.get(loginUrl, headers=self.DEFAULT_OPTIONS['loginHeaders'], allow_redirects=True)

        formRegex = r'<form.+id=\"emailPasswordForm\".*action=\"(?P<formAction>[^\"]+)\"[^>]*>' \
            '(?P<formContent>.+)</form>'
        match = re.search(formRegex, loginResponse.text, flags=re.DOTALL)
        target = match.groupdict()['formAction']

        if not match or not match.groupdict()['formContent']:
            logging.debug('loginResponse: %s', loginResponse.text)
            logging.debug('loginResponse status_code: %d', loginResponse.status_code)
            raise EnvironmentError(
                "%s was not able to find emailPasswordForm"
                % __name__
            )
        inputRegex = r'<input[\\n\\r\s][^/]*name=\"(?P<name>[^\"]+)\"([\\n\\r\s]value=\"(?P<value>[^\"]+)\")?[^/]*/>'
        formData = dict()
        for match in re.finditer(inputRegex, match.groupdict()['formContent']):
            if match.groupdict()['name']:
                formData[match.groupdict()['name']] = match.groupdict()['value']

        formData['email'] = self.username

        # TODO: build from action
        login2Url = 'https://identity.vwgroup.io' + target

        loginHeadersForm = self.DEFAULT_OPTIONS['loginHeaders']
        loginHeadersForm['Content-Type'] = 'application/x-www-form-urlencoded'

        login2Response = self.__session.post(login2Url, headers=loginHeadersForm, data=formData, allow_redirects=True)

        formRegex = r'<form.+id=\"credentialsForm\".*action=\"(?P<formAction>[^\"]+)\"[^>]*>(?P<formContent>.+)</form>'
        match = re.search(formRegex, login2Response.text, flags=re.DOTALL)
        target = match.groupdict()['formAction']

        if not match or not match.groupdict()['formContent']:
            logging.debug('login2Response: %s', login2Response.text)
            logging.debug('login2Response status_code: %d', login2Response.status_code)
            raise EnvironmentError(
                "%s was not able to find credentialsForm"
                % __name__
            )
        inputRegex = r'<input[\\n\\r\s][^/]*name=\"(?P<name>[^\"]+)\"([\\n\\r\s]value=\"(?P<value>[^\"]+)\")?[^/]*/>'
        form2Data = dict()
        for match in re.finditer(inputRegex, match.groupdict()['formContent']):
            if match.groupdict()['name']:
                form2Data[match.groupdict()['name']] = match.groupdict()['value']

        form2Data['password'] = self.password

        # TODO: build from action
        login3Url = 'https://identity.vwgroup.io' + target

        login3Response = self.__session.post(login3Url, headers=loginHeadersForm, data=form2Data, allow_redirects=False)

        if not login3Response.headers['Location']:
            logging.debug('login3Response: %s', login3Response.text)
            logging.debug('login3Response status_code: %d', login3Response.status_code)
            raise EnvironmentError(
                "%s response does not contain Location in Header"
                % __name__
            )

        params = dict(parse.parse_qsl(parse.urlsplit(login3Response.headers['Location']).query))

        if 'error' in params and params['error']:
            logging.debug('login3Response status_code: %d', login3Response.status_code)
            logging.debug('login3Response headers: %s', login3Response.headers)
            logging.debug('login3Response: %s', login3Response.text)
            raise EnvironmentError(
                "%s response contains error parameter Location in Header:"
                % __name__
            )

        if 'userId' not in params or not params['userId']:
            logging.debug('login3Response status_code: %d', login3Response.status_code)
            logging.debug('login3Response headers: %s', login3Response.headers)
            logging.debug('login3Response: %s', login3Response.text)
            raise EnvironmentError(
                "%s response contains no userId parameter in Location in Header:"
                % __name__
            )

        self.__userId = params['userId']

        afterLogingUrl = login3Response.headers['Location']
        while True:
            afterLoginResponse = self.__session.get(
                afterLogingUrl, headers=self.DEFAULT_OPTIONS['loginHeaders'], allow_redirects=False)

            afterLogingUrl = afterLoginResponse.headers['Location']

            if afterLogingUrl.startswith('weconnect://authenticated#'):
                break

        params = dict(parse.parse_qsl(parse.urlsplit(afterLogingUrl.replace('authenticated#', 'authenticated?')).query))

        if all(key in params for key in ('token_type', 'id_token', 'expires_in')):
            self.__token = {
                'type': params['token_type'],
                'token': params['id_token'],
                'expires': datetime.now() + timedelta(seconds=int(params['expires_in']))
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
                self.__token['expires'] = datetime.now() + timedelta(seconds=3600)
                self.__session.auth = BearerAuth(self.__token['token'])
            if 'accessToken' in data:
                self.__aToken['type'] = 'Bearer'
                self.__aToken['token'] = data['accessToken']
                self.__aToken['expires'] = datetime.now() + timedelta(seconds=3600)
            if 'refreshToken' in data:
                self.__rToken['type'] = 'Bearer'
                self.__rToken['token'] = data['refreshToken']
                self.__rToken['expires'] = datetime.now() + timedelta(seconds=3600)

            self.__refreshToken()

    def __refreshToken(self):
        url = 'https://login.apps.emea.vwapps.io/refresh/v1'

        refreshResponse = self.__session.get(url, allow_redirects=False, auth=BearerAuth(self.__rToken['token']))
        data = refreshResponse.json()
        if 'accessToken' in data:
            self.__aToken['type'] = 'Bearer'
            self.__aToken['token'] = data['accessToken']
            self.__aToken['expires'] = datetime.now() + timedelta(seconds=3600)
        else:
            logging.error('No id token received')

        if 'idToken' in data:
            self.__token['type'] = 'Bearer'
            self.__token['token'] = data['idToken']
            self.__token['expires'] = datetime.now() + timedelta(seconds=3600)
            self.__session.auth = BearerAuth(self.__token['token'])
        else:
            logging.error('No id token received')

        if 'refreshToken' in data:
            self.__rToken['type'] = 'Bearer'
            self.__rToken['token'] = data['refreshToken']
            self.__rToken['expires'] = datetime.now() + timedelta(seconds=3600)
        else:
            logging.error('No refresh token received')

        if self.__refreshTimer and self.__refreshTimer.is_alive():
            self.__refreshTimer.cancel()
        self.__refreshTimer = threading.Timer(3600 - 600, self.__refreshToken)
        self.__refreshTimer.daemon = True
        self.__refreshTimer.start()
        logging.info('Token refreshed')

    @property
    def vehicles(self):
        return self.__vehicles

    def update(self):
        url = 'https://mobileapi.apps.emea.vwapps.io/vehicles'

        vehiclesResponse = self.__session.get(url, allow_redirects=False)
        data = vehiclesResponse.json()

        if data['data']:
            vins = list()
            for vehicleDict in data['data']:
                if 'vin' not in vehicleDict:
                    break
                vin = vehicleDict['vin']
                vins.append(vin)
                if vin not in self.__vehicles:
                    vehicle = Vehicle(vin=vin, session=self.__session, parent=self.__vehicles, fromDict=vehicleDict)
                    self.__vehicles[vin] = vehicle
                else:
                    self.__vehicles[vin].update(fromDict=vehicleDict)
            # delete those vins that are not anymore available
            for vin in [vin for vin in vins if vin not in self.__vehicles]:
                del self.__vehicles[vin]

    def getLeafChildren(self):
        return [children for vehicle in self.__vehicles.values() for children in vehicle.getLeafChildren()]
