import typing as t

from pluginable_core.app import AppCloseEvent, PluginableApp

if t.TYPE_CHECKING:
    from pluginable_core.event import Event, EventHandler


class EventNotSupported(NotImplementedError):
    def __init__(self, msg: str, event: "Event", handler: "EventHandler"):
        super().__init__(msg)
        self.event = event
        self.handler = handler


class ContextAlreadyEntered(Exception):
    ...


class MissingContext(Exception):
    ...


class PluginNotRegistered(Exception):
    ...


class PluginAlreadyRegistered(Exception):
    ...


class EventLoopAlreadyRunning(Exception):
    ...


class EventLoopExit(RuntimeError):
    """
    Standard way for exiting event loop - EventHandler's method decided to exit
    event loop. Should be raised from event handling callable only.
    """


class EventLoopAborted(RuntimeError):
    """
    Something went wrong during event handling. Should not be raised from event
    handling function, but from event loop cycle directly.

    It's preferred to use as first expression of ```raise ... from ...```
    statement.
    """
