from urllib3.util.retry import Retry


class BlacklistRetry(Retry):
    def __init__(self, status_blacklist=None, **kwargs):
        self.status_blacklist = status_blacklist
        super().__init__(**kwargs)

    def is_retry(self, method, status_code, has_retry_after=False):
        if self.status_blacklist is not None and status_code in self.status_blacklist:
            return False
        else:
            return super().is_retry(method, status_code, has_retry_after)
