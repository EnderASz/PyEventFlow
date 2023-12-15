import typing as t

from pyeventflow import exc

if t.TYPE_CHECKING:
    from pyeventflow.handler import EventHandler


# TODO: Provide generic type for supported event types
class EventHandlingFunction(t.Protocol):
    def __call__(
        self, handler: "EventHandler", event: t.Any, /
    ) -> t.Awaitable[None | exc.EventLoopExit | Exception]:
        ...
