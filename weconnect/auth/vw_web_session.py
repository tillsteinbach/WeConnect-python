from weconnect.auth.openid_session import OpenIDSession


class VWWebSession(OpenIDSession):
    def __init__(self, sessionuser, **kwargs):
        super(VWWebSession, self).__init__(**kwargs)
        self.sessionuser = sessionuser
