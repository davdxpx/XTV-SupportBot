"""KB repo tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from xtv_support.infrastructure.db import kb as repo
from xtv_support.infrastructure.db.kb import InvalidSlugError


@pytest.mark.parametrize("ok", ["reset-password", "ticket_v2", "a", "a1"])
def test_validate_slug_accepts(ok: str) -> None:
    assert repo.validate_slug(ok) == ok


@pytest.mark.parametrize("bad", ["", "HasCaps", "has space", "-lead", "x" * 65])
def test_validate_slug_rejects(bad: str) -> None:
    with pytest.raises(InvalidSlugError):
        repo.validate_slug(bad)


class _FakeCollection:
    def __init__(self, docs: list[dict] | None = None) -> None:
        self.docs = docs or []
        self.find_one = AsyncMock(return_value=None)
        self.insert_one = AsyncMock(return_value=MagicMock(inserted_id="abc"))
        self.update_one = AsyncMock()
        self.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))

    def find(self, query=None, projection=None):
        docs = (
            list(self.docs)
            if query is None
            else [d for d in self.docs if all(d.get(k) == v for k, v in query.items())]
        )
        return _AsyncCursor(docs)


class _AsyncCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *_a, **_k):
        return self

    def limit(self, _n):
        return self

    def __aiter__(self):
        self._it = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


@pytest.fixture
def db() -> SimpleNamespace:
    return SimpleNamespace(kb_articles=_FakeCollection())


async def test_create_rejects_duplicate_slug(db) -> None:
    db.kb_articles.find_one.return_value = {"slug": "hi"}
    with pytest.raises(ValueError):
        await repo.create(db, slug="hi", title="Hi", body="Hello", created_by=1)


async def test_create_stores_full_document(db) -> None:
    db.kb_articles.find_one.return_value = None
    article = await repo.create(
        db,
        slug="reset-password",
        title="Reset password",
        body="...",
        tags=["auth"],
        project_ids=["support"],
        created_by=7,
    )
    db.kb_articles.insert_one.assert_awaited_once()
    doc = db.kb_articles.insert_one.await_args.args[0]
    assert doc["slug"] == "reset-password"
    assert doc["tags"] == ["auth"]
    assert doc["project_ids"] == ["support"]
    assert doc["views"] == 0
    assert article.tags == ("auth",)


async def test_get_by_slug_parses(db) -> None:
    db.kb_articles.find_one.return_value = {
        "_id": "obj1",
        "slug": "hi",
        "title": "T",
        "body": "B",
        "lang": "en",
        "tags": ["a"],
        "project_ids": [],
        "views": 3,
        "helpful": 2,
        "not_helpful": 1,
    }
    a = await repo.get_by_slug(db, "hi")
    assert a and a.title == "T" and a.views == 3
    assert a.helpfulness == round(2 / 3, 3)


async def test_list_all_filters_by_lang(db) -> None:
    db.kb_articles.docs = [
        {"_id": 1, "slug": "a", "lang": "en", "title": "", "body": ""},
        {"_id": 2, "slug": "b", "lang": "hi", "title": "", "body": ""},
    ]
    items = await repo.list_all(db, lang="en")
    assert [a.slug for a in items] == ["a"]


async def test_update_partial_fields(db) -> None:
    db.kb_articles.update_one.return_value = MagicMock(matched_count=1)
    ok = await repo.update(db, "hi", body="new", tags=["x"])
    assert ok is True
    call = db.kb_articles.update_one.await_args.args
    assert call[0] == {"slug": "hi"}
    set_ = call[1]["$set"]
    assert set_["body"] == "new"
    assert set_["tags"] == ["x"]
    assert "title" not in set_
    assert "updated_at" in set_


async def test_update_missing_returns_false(db) -> None:
    db.kb_articles.update_one.return_value = MagicMock(matched_count=0)
    assert await repo.update(db, "nope", body="x") is False


async def test_delete_returns_bool(db) -> None:
    db.kb_articles.delete_one.return_value = MagicMock(deleted_count=1)
    assert await repo.delete(db, "hi") is True
    db.kb_articles.delete_one.return_value = MagicMock(deleted_count=0)
    assert await repo.delete(db, "nope") is False


async def test_search_empty_query_short_circuits(db) -> None:
    result = await repo.search(db, "")
    assert result == []


async def test_search_applies_text_filter(db) -> None:
    db.kb_articles.docs = []
    await repo.search(db, "password reset", lang="en", project_id="support")
    # The fake doesn't verify the call args but this exercises the
    # filter construction path without raising.


async def test_increment_views(db) -> None:
    await repo.increment_views(db, "slug")
    _, update = db.kb_articles.update_one.await_args.args
    assert update == {"$inc": {"views": 1}}


async def test_record_feedback(db) -> None:
    await repo.record_feedback(db, "slug", helpful=True)
    _, update = db.kb_articles.update_one.await_args.args
    assert update == {"$inc": {"helpful": 1}}

    await repo.record_feedback(db, "slug", helpful=False)
    _, update = db.kb_articles.update_one.await_args.args
    assert update == {"$inc": {"not_helpful": 1}}
