import typing as t
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator

from pyeventflow.proto import EventHandlerMethod


_EventHandlerT = t.TypeVar("_EventHandlerT", bound="EventHandler")


class Event(BaseModel, t.Generic[_EventHandlerT]):
    EVENT_TYPE: str

    @field_validator("EVENT_TYPE")
    def event_type_validator(cls, value: str) -> str:
        if not value.isalnum():
            raise ValueError(
                "Given EVENT_TYPE values is not alphanumeric string."
            )
        return value

    model_config = ConfigDict(frozen=True)

    def get_handler_method(
        self, handler: _EventHandlerT
    ) -> EventHandlerMethod | None:
        return getattr(handler, f"on_{self.EVENT_TYPE.lower()}", None)

    def emit_to(self, handler: _EventHandlerT) -> None:
        # TODO: Should it raise an exception, warning or just ignore it?
        #   I think it should ignore event when handler is not compatible with
        #   it. If some event will be emit to non-compatible event handler, it
        #   won't handle it.
        # if (self.get_handler_method(handler)) is None:
        #     raise EventNotSupported(
        #         f"{self.__class__} event is not supported by: {handler}. "
        #         f"Missing `on_{self.EVENT_TYPE.lower()}` method.",
        #         event=self,
        #         handler=handler,
        #     )

        handler.receive(self)


class EventLoopFlowEventType(StrEnum):
    LOOP_CLOSE_REQUEST = "LOOP_CLOSE_REQUEST"


class EventLoopFlowEvent(Event):
    EVENT_TYPE: EventLoopFlowEventType


class LoopCloseRequestEvent(EventLoopFlowEvent):
    EVENT_TYPE: t.Literal[
        EventLoopFlowEventType.LOOP_CLOSE_REQUEST
    ] = EventLoopFlowEventType.LOOP_CLOSE_REQUEST


class HandlersRunnerFlowEventType(StrEnum):
    LOOP_CLOSE_REQUEST = "LOOP_CLOSE_REQUEST"
    SUB_LOOPS_CLOSE_REQUEST = "SUB_LOOPS_CLOSE_REQUEST"


class HandlersRunnerFlowEvent(Event):
    EVENT_TYPE: HandlersRunnerFlowEventType


class SubLoopsCloseRequestEvent(EventLoopFlowEvent):
    EVENT_TYPE: t.Literal[
        HandlersRunnerFlowEventType.SUB_LOOPS_CLOSE_REQUEST
    ] = HandlersRunnerFlowEventType.SUB_LOOPS_CLOSE_REQUEST
