import typing as t

from pyeventflow.handler import proto


_EventT = t.TypeVar("_EventT")


class EventHandler(proto.EventHandler[_EventT]):
    @t.overload
    def __init__(self, func: proto.EventHandlerCallable[_EventT]) -> None: ...

    @t.overload
    def __init__(
        self, func: proto.EventHandlerCallable[_EventT], handles: set[type[_EventT]]
    ) -> None: ...

    def __init__(
        self,
        func: proto.EventHandlerCallable[_EventT],
        handles: set[type[_EventT]] | None = None,
    ) -> None:
        self.func: proto.EventHandlerCallable[_EventT] = func
        self.handles: set[type[_EventT]] = handles if handles is not None else set()

    def __call__(
        self, handler: proto.HandlersBearerBase, event: _EventT
    ) -> t.Awaitable[None]:
        return self.func(handler, event)


@staticmethod
def event_handler(
    event_type: type[_EventT] = object,
) -> t.Callable[
    [proto.EventHandlerCallable[_EventT] | proto.EventHandler[_EventT]],
    proto.EventHandler[_EventT],
]:
    """
    Decorator factory for wrapping functions into event handlers and marking
    them as compatible with given `event_type`. Event handler marked as
    compatible with given `event_type` is also compatible with its every
    subtype.

    For example let's assume there is a class `B` inheriting from `A`.
        - Event handler compatible with `B` event type will handle only
          events of `B` type.
        - Event handler compatible with `A` event type will handle events
          of type `A` or `B`.
        - Event handler compatible with `object` will handle events of any
          type.

    Args:
        event_type: Event type acceptable by event handler.

    Returns:
        Decorator wrapping function into event handler and marking it as
        compatible with given event type. If EventHandler instead of function
        given, just marks it as compatible with event type and returns it.
    """

    def wrapper(
        handler: proto.EventHandlerCallable[_EventT] | proto.EventHandler[_EventT],
    ) -> proto.EventHandler[_EventT]:
        if isinstance(handler, proto.EventHandler):
            handler.handles.add(event_type)
            return handler
        handles: set[type[_EventT]] = {event_type}
        return EventHandler(handler, handles)

    return wrapper
