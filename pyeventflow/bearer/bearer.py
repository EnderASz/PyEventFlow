from collections import defaultdict
from copy import deepcopy
import inspect
import typing as t

from pyeventflow.bearer import proto


_EventT = t.TypeVar("_EventT")


class HandlersBearerBase(proto.HandlersBearerBase):
    handlers_registry = defaultdict[type, set[proto.EventHandler[object]]](set)

    def __init_subclass__(cls) -> None:
        # Subclass's registry shouldn't modify parent's registry
        cls.handlers_registry = deepcopy(cls.handlers_registry)
        for _, handler in inspect.getmembers(
            cls, lambda obj: isinstance(obj, proto.EventHandler)
        ):
            handler: proto.EventHandler[object]
            for event_type in handler.handles:
                cls.handlers_registry[event_type].add(handler)

        return super().__init_subclass__()

    def _get_event_handlers(
        self, event: _EventT
    ) -> t.Iterator[proto.EventHandler[_EventT]]:
        for parent_type in inspect.getmro(type(event)):
            yield from self.handlers_registry[type(parent_type)]

    async def on_event(self, event: object) -> None:
        for handler in self._get_event_handlers(event):
            await handler(self, event)
