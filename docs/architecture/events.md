# Domain events

Every state change publishes a frozen dataclass on the in-process
`EventBus`. Subscribers run concurrently and failures in one handler
never block the rest.

| Event | Fired by | Notes |
|---|---|---|
| `TicketCreated` | ticket service | includes user, project |
| `TicketAssigned` | assign handler | `assignee_id=None` means cleared |
| `TicketTagged` | tag handler | `tags_added` + `tags_removed` |
| `TicketPriorityChanged` | priority handler | |
| `TicketClosed` | close handler | `reason` ∈ manual / autoclose / resolved |
| `TicketReopened` | reopen handler | |
| `TicketRoutedToTeam` | teams dispatcher | includes `matched_rules` |
| `SlaWarned` | SLA task | one-shot per ticket |
| `SlaBreached` | SLA task | |
| `MessageReceived` / `MessageSent` | message service | |
| `UserBlocked` / `UserUnblocked` / `UserRegistered` / `UserLanguageChanged` | user flows | |
| `BroadcastStarted/Paused/Resumed/Cancelled/Finished` | broadcast service | |
| `ProjectCreated` / `ProjectDeleted` | project admin | |
| `PluginLoaded` / `PluginFailed` / `PluginUnloaded` | plugin loader | |
| `MacroUsed` | macros service | |
| `KbArticleShown` / `KbArticleHelpful` / `KbArticleDismissed` | KB gate | |
| `CsatPrompted` / `CsatReceived` / `CsatCommented` | CSAT service | |

## Subscribing

Via plugin `subscribe_events()` (recommended) or directly:

```python
bus: EventBus = container.resolve(EventBus)

@bus.on(TicketCreated)
async def react(event: TicketCreated):
    ...
```
