# Plugin authoring

Plugins are regular Python packages that expose a `Plugin` class
extending `xtv_support.plugins.base.Plugin`. They can:

- subscribe to domain events via `subscribe_events()`
- register Telegram commands via `register_commands()`
- ship migrations via `migrations()`
- do startup / shutdown work via `on_startup(container)` /
  `on_shutdown()`

```python
from xtv_support.plugins.base import Plugin as BasePlugin, EventSubscription
from xtv_support.domain.events import TicketCreated


class Plugin(BasePlugin):
    name = "my_plugin"
    version = "0.1.0"
    feature_flag = "MY_PLUGIN"

    async def on_startup(self, container):
        self._bus = container.try_resolve(type(self)._bus_type())

    def subscribe_events(self):
        async def on_ticket(event: TicketCreated):
            ...   # do work
        return [EventSubscription(event_type=TicketCreated, handler=on_ticket)]
```

## Discovery

- **Built-ins** live under `src/xtv_support/plugins/builtin/<name>/`
  and are picked up automatically.
- **Third-party** plugins declare the entry-point group
  `xtv_support.plugins` in their own `pyproject.toml`:

  ```toml
  [project.entry-points."xtv_support.plugins"]
  my_plugin = "my_plugin:Plugin"
  ```

## Feature flags

The `feature_flag` attribute gates the plugin on a `FEATURE_*` env
variable. When unset or falsy the loader marks the plugin `disabled`
and skips both startup and event subscriptions.
