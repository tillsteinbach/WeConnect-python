from enum import Enum

import hashlib

import json
import logging

from requests import Session

from weconnect.auth.we_connect_session import WeConnectSession
from weconnect.auth.we_charge_session import WeChargeSession

LOG = logging.getLogger("weconnect")


class SessionUser():
    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password

    def __str__(self) -> str:
        return f'{self.username}:{self.password}'


class Service(Enum):
    WE_CONNECT = 'WeConnect'
    WE_CHARGE = 'WeCharge'

    def __str__(self) -> str:
        return self.value


class SessionManager():
    def __init__(self, tokenstorefile=None) -> None:
        if tokenstorefile is not None:
            try:
                with open(tokenstorefile, 'r', encoding='utf8') as file:
                    self.tokenstore = json.load(file)
            except json.JSONDecodeError as err:
                LOG.info('Could not use token from file %s (%s)', tokenstorefile, err.msg)
                self.tokenstore = {}
            except FileNotFoundError as err:
                LOG.info('Could not use token from file %s (%s)', tokenstorefile, err)
                self.tokenstore = {}
        else:
            self.tokenstore = {}
        self.sessions = {}

    def generateHash(service: Service, sessionuser: SessionUser) -> str:
        hashstr = service.value + str(sessionuser)
        return hashlib.sha512(hashstr.encode()).hexdigest()

    def getSession(self, service: Service, sessionuser: SessionUser) -> Session:
        session = None
        if (service, sessionuser) in self.sessions:
            return self.sessions[(service, sessionuser)]

        hash: str = SessionManager.generateHash(service, sessionuser)
        if hash in self.tokenstore:
            LOG.info('Reusing tokens from previous session')
            token = self.tokenstore[hash]
        else:
            token = None

        if service == Service.WE_CONNECT:
            session = WeConnectSession(sessionuser=sessionuser, token=token)
        elif service == Service.WE_CHARGE:
            session = WeChargeSession(sessionuser=sessionuser, token=token)
        self.sessions[(service, sessionuser)] = session
        return session

    def saveTokenstore(self, filename: str):
        refreshedTokenstore = {}
        for sessionkey, session in self.sessions.items():
            refreshedTokenstore[SessionManager.generateHash(sessionkey[0], sessionkey[1])] = session.token
        self.tokenstore = refreshedTokenstore
        if self.tokenstore:
            try:
                with open(filename, 'w', encoding='utf8') as file:
                    json.dump(self.tokenstore, file)
                LOG.info('Writing tokenstore to file %s', filename)
            except ValueError as err:  # pragma: no cover
                LOG.info('Could not write tokenstore to file %s (%s)', filename, err)
