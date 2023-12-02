import typing as t

if t.TYPE_CHECKING:
    from pyeventflow.event import Event
    from pyeventflow.handler import EventHandler


_EventHandlerT_co = t.TypeVar(
    "_EventHandlerT_co", bound="EventHandler", covariant=True
)


class EventHandlerMethod(t.Protocol):
    def __call__(  # type: ignore
        self: _EventHandlerT_co, event: "Event", /
    ) -> t.Awaitable[None]:
        ...
