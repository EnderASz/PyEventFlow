import abc
import itertools
import typing as t
import asyncio

from pluginable_core import exc
from pluginable_core.event import (
    LoopCloseRequestEvent,
    SubLoopsCloseRequestEvent,
    EventLoopFlowEvent,
    HandlersRunnerFlowEvent,
)

_EventT = t.TypeVar("_EventT", bound="Event")


class EventHandler(t.Generic[_EventT]):
    def __init__(self) -> None:
        self._loop_lock = asyncio.Lock()
        self._event_queue: asyncio.Queue[
            _EventT | EventLoopFlowEvent
        ] = asyncio.Queue()

    @property
    def event_loop_running(self) -> bool:
        return self._loop_lock.locked()

    def receive(self, event: _EventT | EventLoopFlowEvent) -> None:
        self._event_queue.put_nowait(event)

    async def before_event_loop(self) -> None:
        pass

    async def wait_for_event(self) -> _EventT | EventLoopFlowEvent:
        return await self._event_queue.get()

    async def _event_loop(self) -> t.AsyncGenerator[None, None]:
        while True:
            event = await self.wait_for_event()
            try:
                if (
                    handler_method := event.get_handler_method(self)
                ) is not None:
                    await handler_method(event)
            except exc.EventLoopExit:
                break
            except Exception as e:
                raise exc.EventLoopAborted(
                    f"Event loop of {self} has been aborted, due to "
                    f"exception occurrence."
                ) from e
            yield

    async def after_event(self) -> None:
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

    async def on_loop_close_request(
        self, event: "LoopCloseRequestEvent", /
    ) -> None:
        raise exc.EventLoopExit()


class EventHandlersRunner(
    t.Generic[_EventT],
    EventHandler[_EventT | HandlersRunnerFlowEvent],
    abc.ABC,
):
    def __init__(self):
        super().__init__()
        self._runner_lock = asyncio.Lock()

    @abc.abstractmethod
    async def get_sub_handlers(self) -> tuple[EventHandler]:
        ...

    @property
    def running(self) -> bool:
        return self._runner_lock.locked()

    async def run_event_loop(
        self,
    ) -> None:
        async with self._runner_lock:
            main_loop = asyncio.create_task(super().run_event_loop())

            sub_handlers = await self.get_sub_handlers()

            sub_handlers_wait = (
                asyncio.create_task(
                    asyncio.wait(
                        (
                            asyncio.create_task(handler.run_event_loop())
                            for handler in sub_handlers
                        ),
                        return_when=asyncio.FIRST_EXCEPTION,
                    )
                )
                if len(sub_handlers) != 0
                else None
            )

            first_exited, _ = await asyncio.wait(
                (
                    main_loop,
                    sub_handlers_wait,
                )
                if sub_handlers_wait is not None
                else (main_loop,),
                return_when=asyncio.FIRST_COMPLETED,
            )

            exceptions = []

            if first_exited is not main_loop:
                SubLoopsCloseRequestEvent().emit_to(self)

            # If main loop is exited, then it emitted close request to sub handlers
            if sub_handlers_wait is not None:
                done, pending = await sub_handlers_wait
                for task in itertools.chain(done, pending):
                    try:
                        await task
                    except Exception as e:
                        exceptions.append(e)

            LoopCloseRequestEvent().emit_to(self)

            try:
                await main_loop
            except Exception as e:
                exceptions.append(e)

            if len(exceptions) == 0:
                return
            if len(exceptions) == 1:
                raise exceptions[0]

            raise ExceptionGroup(
                "Many event loops raised exceptions", exceptions
            )

    async def emit_sub_loop_close_requests(self) -> None:
        for handler in await self.get_sub_handlers():
            LoopCloseRequestEvent().emit_to(handler)

    async def after_event_loop(
        self, exception: BaseException | None = None
    ) -> bool:
        await self.emit_sub_loop_close_requests()
        return await super().after_event_loop(exception)

    async def on_sub_loops_close_request(
        self, event: SubLoopsCloseRequestEvent, /
    ) -> None:
        await self.emit_sub_loop_close_requests()
