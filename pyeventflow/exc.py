class ContextNotEntered(RuntimeError):
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
