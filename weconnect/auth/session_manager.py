from enum import Enum

from requests import Session
from requests.models import CaseInsensitiveDict

from weconnect.auth.we_connect_session import WeConnectSession
from weconnect.auth.we_charge_session import WeChargeSession


class SessionUser():
    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password


class Service(Enum):
    WE_CONNECT = 'WeConnect'
    WE_CHARGE = 'WeCharge'


class SessionManager():
    def getSession(service: Service, sessionuser: SessionUser) -> Session:
        session = None
        if service == Service.WE_CONNECT:
            session = WeConnectSession(sessionuser=sessionuser)
        elif service == Service.WE_CHARGE:
            session = WeChargeSession(sessionuser=sessionuser)
        return session
