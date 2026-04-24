"""Admin commands for the Phase 4.2 project-template system.

Two entry points (keeps the blast radius small; the full wizard
integration lives in a follow-up inside the same phase):

- ``/templates`` — list available templates with slug, icon, one-line
  description.
- ``/project_template <slug> <project_slug> [name…]`` — install the named
  template into a new project with the given slug. Fails if the slug
  already exists.
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.filters import is_admin_user, is_private
from xtv_support.core.logger import get_logger
from xtv_support.services.templates import default_registry, install_template

log = get_logger("admin.templates")


def _render_list() -> str:
    lines: list[str] = ["<b>Project templates</b>", ""]
    for tmpl in default_registry.list():
        lines.append(f"{tmpl.icon}  <b>{tmpl.slug}</b>  — {tmpl.name}")
        lines.append(f"<i>{tmpl.description}</i>")
        lines.append("")
    lines.append(
        "Install with:  <code>/project_template &lt;slug&gt; &lt;project_slug&gt; [name…]</code>"
    )
    return "\n".join(lines).rstrip()


@Client.on_message(
    filters.command("templates") & is_admin_user & is_private,
    group=HandlerGroup.COMMAND,
)
async def list_templates(_client: Client, message: Message) -> None:
    await message.reply(_render_list(), disable_web_page_preview=True)


@Client.on_message(
    filters.command("project_template") & is_admin_user & is_private,
    group=HandlerGroup.COMMAND,
)
async def install_from_template(client: Client, message: Message) -> None:
    parts = (message.text or "").split(maxsplit=3)
    if len(parts) < 3:
        await message.reply(
            "Usage: <code>/project_template &lt;template_slug&gt; &lt;project_slug&gt; [name…]</code>\n"
            "Run <code>/templates</code> to see available templates."
        )
        return

    template_slug = parts[1].strip()
    project_slug = parts[2].strip()
    project_name = parts[3].strip() if len(parts) == 4 else None

    template = default_registry.get(template_slug)
    if template is None:
        await message.reply(
            f"Unknown template <code>{template_slug}</code>. "
            f"Available: {', '.join(default_registry.slugs())}"
        )
        return

    ctx = get_context(client)
    actor_id = message.from_user.id if message.from_user else 0
    result = await install_template(
        ctx.db,
        ctx.bus,
        template=template,
        project_slug=project_slug,
        project_name=project_name,
        installed_by=actor_id,
    )

    if not result.ok:
        await message.reply(f"❌ Install failed: <code>{result.detail or 'unknown'}</code>")
        return

    hint = f"\n<i>{template.post_install_hint}</i>" if template.post_install_hint else ""
    await message.reply(
        f"✅ Installed <b>{template.name}</b> as project "
        f"<code>{project_slug}</code>\n"
        f"• Macros seeded: {result.macros_seeded}\n"
        f"• KB articles seeded: {result.kb_articles_seeded}\n"
        f"• Routing rules seeded: {result.routing_rules_seeded}"
        f"{hint}"
    )
