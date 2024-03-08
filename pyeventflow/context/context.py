import abc
import asyncio
import contextlib
import typing as t
from types import TracebackType

from pyeventflow.context import exc


class AsyncContextStackManager:
    def __init__(self) -> None:
        self.__context_stack: contextlib.AsyncExitStack | None = None
        self.__context_lock = asyncio.Lock()
        self.__context_exiting_lock = asyncio.Lock()

    @property
    def context_entered(self) -> bool:
        return self.__context_lock.locked()

    @property
    def context_exiting(self) -> bool:
        return self.__context_exiting_lock.locked()

    @abc.abstractmethod
    async def _establish_context(
        self, context_stack: contextlib.AsyncExitStack
    ) -> contextlib.AsyncExitStack: ...

    async def __aenter__(self) -> t.Self:
        if self.context_entered:
            raise exc.ContextAlreadyEntered(
                f"Cannot re-enter context of {self}. Please, exit its current "
                f"context first"
            )

        async with contextlib.AsyncExitStack() as context_stack:
            await context_stack.enter_async_context(self.__context_lock)
            context_stack = await self._establish_context(context_stack)
            self.__context_stack = context_stack.pop_all()

        return self

    async def __aexit__(
        self,
        exc_type: t.Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        if self.context_exiting:
            raise exc.ContextCurrentlyExits(
                f"Cannot exit context of {self}, because it's already exiting"
            )

        async with self.__context_exiting_lock:
            if self.__context_stack is None:
                raise exc.ContextNotEntered(
                    "Tried to exit from not-entered context stack"
                )
            try:
                return await self.__context_stack.__aexit__(exc_type, exc_val, exc_tb)
            finally:
                self.__context_stack = None
