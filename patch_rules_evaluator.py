with open("src/xtv_support/services/rules/evaluator.py") as f:
    content = f.read()

content = content.replace(
    """    def __init__(
        self,
        *,
        db: AsyncIOMotorDatabase,
        bus: EventBus,
        actions: ActionExecutor,
        client: Client | None = None,
    ) -> None:""",
    """    def __init__(
        self,
        *,
        db: AsyncIOMotorDatabase,
        bus: EventBus,
        actions: ActionExecutor,
        container: Container,
        client: Client | None = None,
    ) -> None:""",
)

content = content.replace(
    """        self._db = db
        self._bus = bus
        self._actions = actions
        self._client = client""",
    """        self._db = db
        self._bus = bus
        self._actions = actions
        self._container = container
        self._client = client""",
)

# We need to import Container and DirectoryProviderLike
if "from xtv_support.core.container import Container" not in content:
    content = content.replace(
        "from typing import TYPE_CHECKING, Any",
        "from typing import TYPE_CHECKING, Any\n\nfrom xtv_support.core.container import Container\nfrom xtv_support.services.external_directory.model import DirectoryProviderLike",
    )

content = content.replace(
    """    async def _try_fire(
        self,
        rule: Rule,
        *,
        trigger: str,
        ticket_id: str | None,
        ticket: dict | None,
    ) -> None:
        if ticket is not None and not all_conditions_match(rule.conditions, ticket):""",
    """    async def _try_fire(
        self,
        rule: Rule,
        *,
        trigger: str,
        ticket_id: str | None,
        ticket: dict | None,
    ) -> None:
        user_signal = None
        if ticket is not None:
            user_id = ticket.get("user_id")
            if user_id:
                provider = self._container.resolve(DirectoryProviderLike)
                user_signal = await provider.get_signal(user_id)
        if ticket is not None and not all_conditions_match(rule.conditions, ticket, user_signal=user_signal):""",
)

with open("src/xtv_support/services/rules/evaluator.py", "w") as f:
    f.write(content)
