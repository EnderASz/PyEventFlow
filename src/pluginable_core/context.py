import contextlib
import typing as t
from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self


class AbstractAsyncContextStackManager(
    contextlib.AbstractAsyncContextManager, ABC
):
    def __init__(self) -> None:
        self._context_stack: contextlib.AsyncExitStack | None = None

    @property
    def context_entered(self) -> bool:
        return self._context_stack is not None

    @abstractmethod
    async def _establish_context(
        self, context_stack: contextlib.AsyncExitStack
    ) -> contextlib.AsyncExitStack:
        ...

    async def __aenter__(self) -> Self:
        if self.context_entered:
            return self

        context_stack = contextlib.AsyncExitStack()
        async with context_stack:
            context_stack = await self._establish_context(context_stack)
            self._context_stack = context_stack.pop_all()

        return self

    async def __aexit__(
        self,
        exc_type: t.Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        if self._context_stack is None:
            return None

        await self._context_stack.aclose()
        self._context_stack = None
        return None
