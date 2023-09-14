import contextlib
import typing as t

from pluginable_core import exc
from pluginable_core.context import AsyncContextStackManager
from pluginable_core.event import Event, EventHandler


_PluginsBearerT = t.TypeVar(
    "_PluginsBearerT", bound="PluginsBearer", covariant=True
)
_PluginT = t.TypeVar("_PluginT", bound="Plugin")


class PluginsBearer(t.Generic[_PluginT], AsyncContextStackManager):
    def __init__(self):
        super().__init__()
        self._plugins: list[_PluginT] = []

    @property
    def plugins(self) -> t.Sequence[_PluginT]:
        return tuple(self._plugins)

    async def _establish_context(
        self, context_stack: contextlib.AsyncExitStack
    ) -> contextlib.AsyncExitStack:
        for plugin in self.plugins:
            await context_stack.enter_async_context(plugin)

        return context_stack

    def register(self, plugin: _PluginT) -> None:
        """
        Registers and bounds plugin.

        :param plugin: Plugin instance
        """
        if self.context_entered:
            raise exc.ContextAlreadyEntered(
                "Cannot register plugin to already context entered bearer"
            )

        if plugin.bearer is not None:
            raise exc.PluginAlreadyRegistered(
                "Cannot register plugin that is already registered at any "
                "plugin plugin bearer"
            )

        self._plugins.append(plugin)
        plugin._bearer = self

    def unregister(self, plugin: _PluginT) -> None:
        """
        Unregisters and unbound plugin..
        :param plugin:
        """
        if self.context_entered:
            raise exc.ContextAlreadyEntered(
                "Cannot unregister plugin from already context entered bearer"
            )
        if plugin.bearer is not self:
            raise exc.PluginNotRegistered(
                f"{self} cannot unregister non-registered plugin."
            )
        self._plugins.remove(plugin)
        plugin._bearer = None

    def emit(self, event: "Event") -> None:
        """
        Emits given event to plugins.

        :param event:
        """
        for plugin in self.plugins:
            if isinstance(plugin, EventHandlingPlugin):
                event.emit_to(plugin)


class Plugin(t.Generic[_PluginsBearerT], AsyncContextStackManager):
    def __init__(self):
        super().__init__()
        self._bearer: _PluginsBearerT | None = None

    @property
    def bearer(self) -> _PluginsBearerT | None:
        return self._bearer

    async def run(self) -> None:
        pass


class EventHandlingPlugin(
    t.Generic[_PluginsBearerT], Plugin[_PluginsBearerT], EventHandler
):
    async def run(self) -> None:
        await self.run_event_loop()
