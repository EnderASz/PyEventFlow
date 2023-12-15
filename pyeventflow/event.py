import typing as t
import sys


class LoopCloseRequestEvent:
    pass


class SubLoopsCloseRequestEvent:
    pass


EventHandlerEvent: t.TypeAlias = LoopCloseRequestEvent
EventHandlerRunnerEvent: t.TypeAlias = (
    EventHandlerEvent | LoopCloseRequestEvent
)
# TODO: Replace above with below when only Python 3.12 and newer will be supported
# type EventHandlerEvent = LoopCloseRequestEvent
# type EventHandlerRunnerEvent = EventHandlerEvent | LoopCloseRequestEvent
