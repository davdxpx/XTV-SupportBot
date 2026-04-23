"""/kb admin command — CRUD for knowledge-base articles.

Grammar
-------
``/kb list [lang]``                              — list articles
``/kb show <slug>``                              — print an article
``/kb add <slug> | <title>`` then reply/text     — start creation
``/kb add <slug> | <title> | <body>``            — inline one-shot
``/kb edit <slug>`` then reply/text              — replace body
``/kb edit <slug> body: <text>``                 — inline body change
``/kb edit <slug> title: <text>``                — inline title change
``/kb edit <slug> tags: tag1,tag2,…``            — replace tags
``/kb del <slug>``                               — delete an article
``/kb search <query>``                           — full-text search
"""
from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.errors import AdminOnly
from xtv_support.core.logger import get_logger
from xtv_support.core.rbac import require
from xtv_support.domain.enums import Role
from xtv_support.infrastructure.db import kb as kb_repo
from xtv_support.infrastructure.db.kb import InvalidSlugError
from xtv_support.services.kb import service as kb_service

log = get_logger("kb_cmd")

USAGE = (
    "<b>/kb</b>\n"
    "  /kb list [lang]\n"
    "  /kb show &lt;slug&gt;\n"
    "  /kb add &lt;slug&gt; | &lt;title&gt; | &lt;body&gt;\n"
    "  /kb edit &lt;slug&gt; body: &lt;text&gt; | title: &lt;text&gt; | tags: a,b\n"
    "  /kb del &lt;slug&gt;\n"
    "  /kb search &lt;query&gt;"
)


def _rest(message: Message) -> str:
    parts = (message.text or "").strip().split(maxsplit=1)
    return parts[1] if len(parts) == 2 else ""


def _split_pipe(s: str, *, parts: int) -> list[str]:
    """Split ``A | B | C`` into exactly ``parts`` trimmed pieces."""
    out = [p.strip() for p in s.split("|", maxsplit=parts - 1)]
    while len(out) < parts:
        out.append("")
    return out[:parts]


@Client.on_message(filters.private & filters.command("kb"), group=HandlerGroup.COMMAND)
async def kb_cmd(client: Client, message: Message) -> None:
    try:
        require(Role.SUPERVISOR)
    except AdminOnly:
        await message.reply_text("🚫 Supervisor role required.")
        return

    ctx = get_context(client)
    rest = _rest(message)
    if not rest:
        await message.reply_text(USAGE)
        return

    sub, _, rest = rest.partition(" ")
    sub = sub.lower()
    rest = rest.strip()

    try:
        if sub == "list":
            await _list(ctx, message, rest)
        elif sub == "show":
            await _show(ctx, message, rest)
        elif sub == "add":
            await _add(ctx, message, rest)
        elif sub == "edit":
            await _edit(ctx, message, rest)
        elif sub in ("del", "delete", "rm"):
            await _delete(ctx, message, rest)
        elif sub == "search":
            await _search(ctx, message, rest)
        else:
            await message.reply_text(USAGE)
    except InvalidSlugError as exc:
        await message.reply_text(f"⚠️ {exc}")
    except Exception as exc:  # noqa: BLE001
        log.exception("kb_cmd.failed", sub=sub, error=str(exc))
        await message.reply_text(f"❌ Error: {exc}")


# ----------------------------------------------------------------------
# Subcommands
# ----------------------------------------------------------------------
async def _list(ctx, message: Message, rest: str) -> None:
    lang = rest.strip().split()[0] if rest.strip() else None
    articles = await kb_repo.list_all(ctx.db, lang=lang, limit=50)
    if not articles:
        await message.reply_text(
            "No articles found." + (f" (lang={lang})" if lang else "")
        )
        return
    lines = [f"<b>KB articles ({len(articles)})</b>"]
    for a in articles:
        tags = ",".join(a.tags) if a.tags else "—"
        lines.append(
            f"  • <code>{a.slug}</code> [{a.lang}] — {a.title} · "
            f"views={a.views} · 👍{a.helpful}/👎{a.not_helpful} · tags={tags}"
        )
    await message.reply_text("\n".join(lines))


async def _show(ctx, message: Message, rest: str) -> None:
    slug = rest.strip().split()[0] if rest.strip() else ""
    if not slug:
        await message.reply_text("Usage: <code>/kb show &lt;slug&gt;</code>")
        return
    article = await kb_repo.get_by_slug(ctx.db, slug)
    if article is None:
        await message.reply_text(f"No article <code>{slug}</code>.")
        return
    tags = ", ".join(article.tags) if article.tags else "—"
    helpfulness = f"{int(article.helpfulness * 100)}%" if (article.helpful + article.not_helpful) else "—"
    await message.reply_text(
        f"<b>{article.title}</b> (<code>{article.slug}</code>)\n"
        f"lang={article.lang} · tags={tags} · views={article.views} · "
        f"helpful={helpfulness}\n\n"
        f"<blockquote expandable>{article.body}</blockquote>"
    )


async def _add(ctx, message: Message, rest: str) -> None:
    # Split by "|" — slug | title | body (body optional if replying).
    slug, title, body = _split_pipe(rest, parts=3)
    if not slug or not title:
        await message.reply_text(
            "Usage: <code>/kb add &lt;slug&gt; | &lt;title&gt; | &lt;body&gt;</code>"
        )
        return
    if not body and message.reply_to_message:
        body = message.reply_to_message.text or message.reply_to_message.caption or ""
    if not body:
        await message.reply_text(
            "Provide the body inline after a third '|' or reply to a message."
        )
        return
    try:
        article = await kb_repo.create(
            ctx.db,
            slug=slug,
            title=title,
            body=body,
            created_by=message.from_user.id,
        )
    except ValueError as exc:
        await message.reply_text(f"⚠️ {exc}")
        return
    log.info("kb.created", slug=slug, title=title, by=message.from_user.id)
    await message.reply_text(f"✅ Created <code>{article.slug}</code> — {article.title}.")


async def _edit(ctx, message: Message, rest: str) -> None:
    # Format: ``<slug> key: value``
    parts = rest.split(maxsplit=1)
    if not parts:
        await message.reply_text(
            "Usage: <code>/kb edit &lt;slug&gt; body: &lt;text&gt; | title: &lt;text&gt; | tags: a,b</code>"
        )
        return
    slug = parts[0]
    kv = parts[1] if len(parts) == 2 else ""
    if not kv:
        await message.reply_text("Missing body/title/tags payload.")
        return
    key, _, value = kv.partition(":")
    key = key.strip().lower()
    value = value.strip()
    if not key or not value:
        await message.reply_text("Invalid payload. Use <code>key: value</code>.")
        return

    kwargs: dict = {}
    if key == "body":
        kwargs["body"] = value
    elif key == "title":
        kwargs["title"] = value
    elif key == "tags":
        kwargs["tags"] = [t.strip() for t in value.split(",") if t.strip()]
    elif key == "lang":
        kwargs["lang"] = value
    else:
        await message.reply_text(f"Unknown key {key!r}.")
        return

    updated = await kb_repo.update(ctx.db, slug, **kwargs)
    if updated:
        log.info("kb.updated", slug=slug, field=key, by=message.from_user.id)
        await message.reply_text(f"✅ Updated <code>{slug}</code> ({key}).")
    else:
        await message.reply_text(f"No article <code>{slug}</code>.")


async def _delete(ctx, message: Message, rest: str) -> None:
    slug = rest.strip().split()[0] if rest.strip() else ""
    if not slug:
        await message.reply_text("Usage: <code>/kb del &lt;slug&gt;</code>")
        return
    removed = await kb_repo.delete(ctx.db, slug)
    if removed:
        log.info("kb.deleted", slug=slug, by=message.from_user.id)
        await message.reply_text(f"🗑️ Deleted <code>{slug}</code>.")
    else:
        await message.reply_text(f"No article <code>{slug}</code>.")


async def _search(ctx, message: Message, rest: str) -> None:
    if not rest.strip():
        await message.reply_text("Usage: <code>/kb search &lt;query&gt;</code>")
        return
    results = await kb_service.search(ctx.db, rest, limit=10)
    if not results:
        await message.reply_text("No matches.")
        return
    lines = [f"<b>Search: {rest}</b>"]
    for i, a in enumerate(results, 1):
        lines.append(f"  {i}. <code>{a.slug}</code> [{a.lang}] — {a.title}")
    await message.reply_text("\n".join(lines))

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
