import asyncio
import contextlib
import typing as t
from types import TracebackType
from typing import Self

from pyflow import exc


class AsyncContextStackManager(contextlib.AbstractAsyncContextManager):
    def __init__(self) -> None:
        self.__context_stack: contextlib.AsyncExitStack | None = None
        self.__context_lock = asyncio.Lock()

    @property
    def context_entered(self) -> bool:
        return self.__context_lock.locked()

    async def _establish_context(
        self, context_stack: contextlib.AsyncExitStack
    ) -> contextlib.AsyncExitStack:
        await context_stack.enter_async_context(self.__context_lock)
        return context_stack

    async def __aenter__(self) -> Self:
        context_stack = contextlib.AsyncExitStack()
        async with context_stack:
            context_stack = await self._establish_context(context_stack)
            self.__context_stack = context_stack.pop_all()

        return self

    async def __aexit__(
        self,
        exc_type: t.Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        if self.__context_stack is None:
            raise exc.ContextNotEntered(
                "Tried to exit from not-entered context stack"
            )

        await self.__context_stack.aclose()
        self.__context_stack = None
        return None
