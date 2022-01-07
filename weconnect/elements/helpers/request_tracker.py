from typing import TYPE_CHECKING, Tuple
from datetime import datetime, timedelta
from threading import Timer

if TYPE_CHECKING:
    from weconnect.elements.vehicle import Vehicle

from weconnect.elements.generic_status import GenericStatus
from weconnect.domain import Domain


class RequestTracker:
    def __init__(self, vehicle: 'Vehicle') -> None:
        self.vehicle: 'Vehicle' = vehicle
        self.requests: dict[Domain, list[Tuple[str, datetime, datetime]]] = {}
        self.__timer = None

    def clear(self) -> None:
        self.requests.clear()
        if self.__timer is not None or self.__timer.is_alive():
            self.__timer.cancel()

    def trackRequest(self, id: str, domain: Domain, minTime: int, maxTime: int) -> None:
        minDate = datetime.now() + timedelta(seconds=minTime)
        maxDate = datetime.now() + timedelta(seconds=maxTime)
        if domain not in self.requests:
            self.requests[domain] = [(id, minDate, maxDate)]
        else:
            self.requests[domain].append((id, minDate, maxDate))

        if self.__timer is None or not self.__timer.is_alive():
            self.__timer = Timer(5, self.update)
            self.__timer.daemon = True
            self.__timer.start()

    def update(self) -> None:  # noqa: C901
        self.vehicle.updateStatus(force=True, selective=self.requests)
        openRequests = []
        for domain, statuses in self.vehicle.domains.items():
            for status in statuses.values():
                if status.hasRequests():
                    openRequests.extend(status.requests)

        for domain, requests in list(self.requests.items()):
            for request in requests:
                id, minDate, maxDate = request

                if maxDate < datetime.now():
                    requests.remove(request)
                else:
                    for openRequest in openRequests:
                        if openRequest.requestId.value == id:
                            if openRequest.status.value not in (GenericStatus.Request.Status.IN_PROGRESS,
                                                                GenericStatus.Request.Status.QUEUED,
                                                                GenericStatus.Request.Status.DELAYED):
                                requests.remove(request)
                            request = (id, datetime.now(), maxDate)
            if not requests:
                self.requests.pop(domain)

        self.__timer = Timer(5, self.update)
        self.__timer.daemon = True
        self.__timer.start()
