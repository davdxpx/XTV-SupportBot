"""admin_accounts repository — case-insensitive uniqueness + TOCTOU."""

from __future__ import annotations

import pytest
from mongomock_motor import AsyncMongoMockClient

from xtv_support.api.routes.auth import username_syntax_ok
from xtv_support.infrastructure.db import admin_accounts as repo
from xtv_support.infrastructure.db import migrations


@pytest.fixture
async def db():
    d = AsyncMongoMockClient().testdb
    await migrations.ensure_indexes(d)
    return d


async def _create(db, username, tg=555):
    return await repo.create(
        db,
        username=username,
        display_username=username,
        first_name="X",
        last_name=None,
        password_hash="h",
        telegram_user_id=tg,
        created_via_key_id="k",
    )


async def test_create_and_lookup_lowercases(db) -> None:
    acc = await _create(db, "DavidK")
    assert acc.username == "davidk"
    assert acc.display_username == "DavidK"
    assert (await repo.get_by_username(db, "DAVIDK")).id == acc.id
    assert await repo.get_by_id(db, acc.id) is not None


async def test_username_taken_case_insensitive(db) -> None:
    await _create(db, "DavidK")
    assert await repo.username_taken(db, "davidk") is True
    assert await repo.username_taken(db, "DAVIDK") is True
    assert await repo.username_taken(db, "someoneelse") is False


async def test_duplicate_insert_raises_username_taken(db) -> None:
    await _create(db, "davidk")
    with pytest.raises(repo.UsernameTaken):
        await _create(db, "DavidK", tg=999)


async def test_set_disabled_and_list(db) -> None:
    acc = await _create(db, "agent1")
    await repo.set_disabled(db, acc.id, disabled=True)
    assert len(await repo.list_all(db, include_disabled=False)) == 0
    assert len(await repo.list_all(db, include_disabled=True)) == 1
    await repo.set_disabled(db, acc.id, disabled=False)
    assert len(await repo.list_all(db, include_disabled=False)) == 1


@pytest.mark.parametrize("u", ["ab", "1abc", "has space", "has-dash", "x" * 33, "", "a!"])
def test_username_syntax_invalid(u: str) -> None:
    assert username_syntax_ok(u) is False


@pytest.mark.parametrize("u", ["abc", "DavidK", "a_b_c", "User123", "x" * 32])
def test_username_syntax_valid(u: str) -> None:
    assert username_syntax_ok(u) is True
