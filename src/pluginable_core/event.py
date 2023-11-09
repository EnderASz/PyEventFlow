import asyncio
import typing as t

from pydantic import BaseModel, ConfigDict, field_validator

from pluginable_core import exc


_EventT = t.TypeVar("_EventT", bound="Event")


class EventHandler(t.Generic[_EventT]):
    def __init__(self) -> None:
        self._loop_lock = asyncio.Lock()
        self._event_queue: asyncio.Queue[_EventT] = asyncio.Queue()

    @property
    def event_loop_running(self):
        return self._loop_lock.locked()

    def receive(self, event: _EventT):
        self._event_queue.put_nowait(event)

    async def before_event_loop(self) -> None:
        pass

    async def wait_for_event(self) -> _EventT:
        return await self._event_queue.get()

    async def _event_loop(self) -> t.AsyncGenerator[None, None]:
        while True:
            event = await self.wait_for_event()
            try:
                if (
                    handler_method := event.get_handler_method(self)
                ) is not None:
                    await handler_method(event=event)
            except exc.EventLoopExit:
                break
            except Exception as e:
                raise exc.EventLoopAborted(
                    f"Event loop of {self} has been aborted, due to "
                    f"exception occurrence."
                ) from e
            yield

    async def after_event(self):
        pass

    async def after_event_loop(
        self, exception: BaseException | None = None
    ) -> bool:
        """
        Called every time when event loop ends with EventLoopExit or any other
        exception. If any exception other than ExitEventLoop has been raised,
        it is given as `exception` parameter.

        - If True is returned, exception is suppressed. Otherwise, it will be
          raised further.
        - If no exception is given, return value is simply ignored and nothing
          should be raised further.

        :param exception: Exception raised by event handling function or None
                          if ExitEventLoop was raised.
        :return: Suppress exception flag
        """
        return False

    async def run_event_loop(self) -> None:
        if self.event_loop_running:
            raise exc.EventLoopAlreadyRunning(
                f"You are unable to run {self} event loop for now. It's "
                f"already running. {self.__class__.__name__} instance can "
                f"only run one event loop at the time."
            )
        async with self._loop_lock:
            await self.before_event_loop()

            try:
                async for _ in self._event_loop():
                    await self.after_event()
                    await asyncio.sleep(0)
            except exc.EventLoopAborted as abortion:
                if not await self.after_event_loop(abortion.__cause__):
                    raise
            except Exception as e:
                # No other exception should be raised - even when user broke
                # something and didn't try to modify event loop workflow (with
                # mocks for example).
                raise RuntimeError(
                    "Unexpected exception occurred in event loop cycle."
                ) from e

            await self.after_event_loop()


_EventHandlerT = t.TypeVar("_EventHandlerT", bound=EventHandler)
_EventHandlerT_co = t.TypeVar(
    "_EventHandlerT_co", bound=EventHandler, covariant=True
)


class EventHandlerMethod(t.Protocol):
    def __call__(  # type: ignore
        self: _EventHandlerT_co, *, event: _EventT
    ) -> t.Awaitable[None]:
        ...


class Event(BaseModel, t.Generic[_EventHandlerT]):
    EVENT_TYPE: str

    @field_validator("EVENT_TYPE")
    def event_type_validator(cls, value: str):
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
