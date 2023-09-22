class RetrievalError(Exception):
    pass


class TooManyRequestsError(RetrievalError):
    pass


class SetterError(Exception):
    pass


class ControlError(SetterError):
    pass


class AuthentificationError(Exception):
    pass


class TemporaryAuthentificationError(AuthentificationError):
    pass


class APICompatibilityError(Exception):
    pass


class APIError(Exception):
    pass
