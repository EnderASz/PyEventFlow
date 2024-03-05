import abc
import typing as t

from pyeventflow.handler.proto import EventHandler


_EventT = t.TypeVar("_EventT", bound=object)


class HandlersBearerBase(t.Protocol):
    @abc.abstractmethod
    def _get_event_handlers(self, event: _EventT) -> t.Iterator[EventHandler[_EventT]]:
        """
        Retrieves all registered event handlers compatible with given type of
        event.

        Args:
            event: Event to retrieve handlers for

        Returns:
            Iterator of event handlers compatible with given event
        """
        ...
