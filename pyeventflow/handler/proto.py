import abc
import typing as t


if t.TYPE_CHECKING:
    from pyeventflow.bearer.proto import HandlersBearerBase


_EventT = t.TypeVar("_EventT", bound=object, contravariant=True)


class EventHandlerCallable(t.Protocol[_EventT]):
    @abc.abstractmethod
    def __call__(
        self, handler: "HandlersBearerBase", event: _EventT
    ) -> t.Awaitable[None]: ...


@t.runtime_checkable
class EventHandler(abc.ABC, EventHandlerCallable[_EventT]):
    handles: set[type[_EventT]]
