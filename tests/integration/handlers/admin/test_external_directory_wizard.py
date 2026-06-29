from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pyrogram.types import CallbackQuery, Chat, Message, User

from xtv_support.core.context import HandlerContext
from xtv_support.core.state import MemoryStateStore, StateMachine
from xtv_support.handlers.admin.external_directory_wizard import (
    extdir_callback,
)


@pytest.fixture
def mock_ctx():
    ctx = MagicMock(spec=HandlerContext)
    ctx.db = MagicMock()

    store = MemoryStateStore()
    ctx.state = StateMachine(store)
    return ctx

@pytest.fixture
def mock_client():
    client = MagicMock()
    client.send_message = AsyncMock()
    client.edit_message_text = AsyncMock()
    client.delete_messages = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_admin_only_filter(mock_client, mock_ctx):
    # Setup CQ with non-admin user
    cq = MagicMock(spec=CallbackQuery)
    cq.from_user = User(id=999, is_self=False)
    cq.data = "cb:v2:admin:extdir:entry"
    cq.answer = AsyncMock()

    with patch("xtv_support.handlers.admin.external_directory_wizard.get_context", return_value=mock_ctx), \
         patch("xtv_support.handlers.admin.external_directory_wizard.is_admin", return_value=False):

        await extdir_callback(mock_client, cq)

        cq.answer.assert_called_once_with("Admin only.", show_alert=True)
        mock_client.send_message.assert_not_called()

@pytest.mark.asyncio
async def test_extdir_wizard_cancel_clears_state(mock_client, mock_ctx):
    user_id = 123
    mock_ctx.db.users.find_one = AsyncMock(return_value=None)

    cq = MagicMock(spec=CallbackQuery)
    cq.from_user = User(id=user_id, is_self=False)
    cq.data = "cb:v2:admin:extdir:wizard:cancel"

    msg = Message(id=1, chat=Chat(id=user_id, type="private"))
    msg._client = mock_client
    cq.message = msg

    cq.answer = AsyncMock()

    # Pre-set state to simulate active wizard
    await mock_ctx.state.set(user_id, "extdir_wizard", data={"extdir_db": "test"})

    with patch("xtv_support.handlers.admin.external_directory_wizard.get_context", return_value=mock_ctx), \
         patch("xtv_support.handlers.admin.external_directory_wizard.is_admin", return_value=True):

        await extdir_callback(mock_client, cq)

        # State should be cleared
        val = await mock_ctx.state.current(user_id)
        assert val is None
        mock_client.edit_message_text.assert_called_once()
