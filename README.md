# PyEventFlow
PyEventFlow is a library simplifying development of event-based apps which interacts with internal and remote objects via events.


## Architecture
**Work In Progress**
```mermaid
classDiagram
    class `typing.AbstractAsyncContextManager`
    <<interface>> `typing.AbstractAsyncContextManager`
    class `contextlib.AsyncExitStack`
    
    class Runner
    <<interface>> Runner
%%    <<abstract>> Runner

    class EventListener
    <<abstract>> EventListener
    EventListener --|> Runner
    
    class _HandlersBearerBase
    <<abstract>> _HandlersBearerBase
    _HandlersBearerBase --|> EventListener

    class HandlersBearer
    HandlersBearer --|> _HandlersBearerBase
%%    HandlersBearer --|> EventListener

    class ListenersRunner
    <<abstract>> ListenersRunner
    ListenersRunner --|> Runner
    EventListener "1..*" --o "1" ListenersRunner
    
    class EventHandler
    <<interface>> EventHandler
    EventHandler "1..*" --o "*" HandlersBearer

    class AsyncContextStackManager
    AsyncContextStackManager --|> `typing.AbstractAsyncContextManager`
    
    `contextlib.AsyncExitStack` "1" --* "1" AsyncContextStackManager

```
