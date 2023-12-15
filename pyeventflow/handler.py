import abc
import asyncio
from collections import defaultdict
import inspect
import itertools
import typing as t

from pyeventflow import exc
from pyeventflow.event import (
    EventHandlerEvent,
    LoopCloseRequestEvent,
    SubLoopsCloseRequestEvent,
)
from pyeventflow.proto import EventHandlingFunction


class _HandlerBase:
    # TODO: Provide generic type for supported event types
    _events_registry: dict[type, set[EventHandlingFunction]] = defaultdict(set)

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        for _, method in inspect.getmembers(cls, inspect.isfunction):
            # TODO: Provide generic type for supported event types
            method: EventHandlingFunction
            if hasattr(method, "handle_events"):
                for event_type in method.handle_events:
                    cls._events_registry[event_type].add(method)

    # TODO: Provide generic type for supported event types
    def _get_event_handling_methods(
        self, event: t.Any
    ) -> t.Iterator[EventHandlingFunction]:
        for event_type, handlers in self._events_registry.items():
            if isinstance(event, event_type):
                yield from iter(handlers)

    # TODO: Provide generic type for supported event types
    @staticmethod
    def handling_method(
        event_type: type,
    ) -> t.Callable[[EventHandlingFunction], EventHandlingFunction]:
        """Creates a decorator which marks given callable as handler for
        `event_type`.

        Under the hood this decorator creates a `handle_events` set of event
        types and/or adds given `event_type` to this set.

        Args:
            event_type: type: event type

        Returns:
            Decorator marking given callable as handler for `event_type`
        """

        # TODO: Provide generic type for supported event types
        def marker(handler: EventHandlingFunction) -> EventHandlingFunction:
            if not hasattr(handler, "handle_events"):
                handler.handle_events = {event_type}
                return handler
            handler.handle_events.add(event_type)
            return handler

        return marker


handling_method = _HandlerBase.handling_method


class EventHandler(_HandlerBase):
    def __init__(self) -> None:
        self._loop_lock = asyncio.Lock()
        # TODO: Provide generic type for supported event types
        self._event_queue: asyncio.Queue[
            EventHandlerEvent | t.Any
        ] = asyncio.Queue()

    @property
    def event_loop_running(self) -> bool:
        return self._loop_lock.locked()

    # TODO: Provide generic type for supported event types
    def receive(self, event: EventHandlerEvent | t.Any) -> None:
        self._event_queue.put_nowait(event)

    async def before_event_loop(self) -> None:
        pass

    # TODO: Provide generic type for supported event types
    async def wait_for_event(self) -> EventHandlerEvent | t.Any:
        return await self._event_queue.get()

    async def _event_loop(self) -> t.AsyncGenerator[None, None]:
        abort_reasons: list[Exception] = []

        exit_loop = False
        while True:
            event = await self.wait_for_event()

            methods = self._get_event_handling_methods(event)
            results = await asyncio.gather(
                *(method(self, event) for method in methods), return_exceptions=True
            )
            for result in results:
                # INFO: Handling method can not only raise `EventLoopExit` or
                # any other exception to exit/abort event loop, but they can
                # also return them
                if isinstance(result, exc.EventLoopExit):
                    exit_loop = True
                    continue
                if isinstance(result, Exception):
                    abort_reasons.append(result)
                # Result values other than exceptions are just ignored

            if len(abort_reasons) > 0:
                raise exc.EventLoopAborted(
                    f"Event loop of {self} has been aborted, due to "
                    f"exceptions occurrence."
                ) from ExceptionGroup("", abort_reasons)
            if exit_loop:
                return
            yield

    async def after_event(self) -> None:
        """Method called after the event has been processed.

        This function can be used to clean up any resources that were created
        in the `before_event` method or during event handling.

        Returns:
            None
        """
        pass

    async def after_event_loop(
        self, exception: BaseException | None = None
    ) -> bool:
        """Method called every time when event loop ends with EventLoopExit or
        any other exception. If any exception other than ExitEventLoop has been
         raised, it is given as `exception` parameter.

        Args:
            self
            exception: BaseException | None: Exception raised by event handling
             function or None if `ExitEventLoop` was raised.

        Returns:
            A boolean value
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

    @handling_method(LoopCloseRequestEvent)
    async def on_loop_close_request(self, _: LoopCloseRequestEvent, /) -> None:
        raise exc.EventLoopExit()


class EventHandlersRunner(EventHandler, abc.ABC):
    def __init__(self):
        super().__init__()
        self._runner_lock = asyncio.Lock()

    @abc.abstractmethod
    async def get_sub_handlers(self) -> tuple[EventHandler]:
        ...

    @property
    def running(self) -> bool:
        return self._runner_lock.locked()

    async def run_event_loop(self) -> None:
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
                self.receive(SubLoopsCloseRequestEvent())

            # If main loop is exited, then it emitted close request to sub handlers
            if sub_handlers_wait is not None:
                done, pending = await sub_handlers_wait
                for task in itertools.chain(done, pending):
                    try:
                        await task
                    except Exception as e:
                        exceptions.append(e)

            self.receive(LoopCloseRequestEvent())

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
            handler.receive(LoopCloseRequestEvent())

    async def after_event_loop(
        self, exception: BaseException | None = None
    ) -> bool:
        await self.emit_sub_loop_close_requests()
        return await super().after_event_loop(exception)

    @handling_method(SubLoopsCloseRequestEvent)
    async def on_sub_loops_close_request(
        self, _: SubLoopsCloseRequestEvent, /
    ) -> None:
        await self.emit_sub_loop_close_requests()
