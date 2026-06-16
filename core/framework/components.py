"""
core/framework/components.py  -  Components V2 DSL for Discoin.

``Container()`` is the canonical, fluent entry point for Components V2
layouts. It is the V2 counterpart of ``card()`` in ``core/framework/embed.py``
and is the default for all NEW user-facing surfaces (requires discord.py>=2.6).

Usage::

    from core.framework.components import Container, send_v2, edit_v2
    from core.framework.ui import C_INFO

    panel = (
        Container(color=C_INFO)
        .text("# Wallet")
        .divider()
        .field("Balance", "$1,234.50")
        .section("Tap to refresh", button=refresh_btn)
    )
    await send_v2(ctx, panel)

    # Later, edit in place:
    await edit_v2(msg, panel.text("Updated!"))

Interactive surfaces subclass ``V2View`` (a ``discord.ui.LayoutView`` with
the same author-lock behaviour as the framework's ``ConfirmView``) and add
containers via ``view.add_container(container)``.
"""
from __future__ import annotations

import logging

import discord

log = logging.getLogger(__name__)

# Discord hard limits for Components V2 messages.
_MAX_TEXT_TOTAL = 4000   # total characters across all text displays
_MAX_COMPONENTS = 40     # total component count per message

__all__ = ("Container", "V2View", "send_v2", "edit_v2")


class Container:
    """
    Fluent Components V2 container builder.

    All methods return ``self`` so calls can be chained. Pass the finished
    builder to ``send_v2()`` / ``edit_v2()``, or call ``.build()`` to get a
    ready-to-send ``discord.ui.LayoutView``.
    """

    __slots__ = ("_color", "_spoiler", "_items", "_text_total")

    def __init__(self, *, color: int | None = None, spoiler: bool = False) -> None:
        self._color = color
        self._spoiler = spoiler
        self._items: list[discord.ui.Item] = []
        self._text_total = 0

    # ── Content ────────────────────────────────────────────────────────────

    def text(self, *lines: str) -> "Container":
        """Add a text display. Multiple args are joined with newlines.

        Markdown works here, including ``#`` headings -- use ``# Title`` for
        what would have been the embed title.
        """
        content = "\n".join(lines)
        self._items.append(discord.ui.TextDisplay(self._clamp(content)))
        return self

    def text_if(self, condition: bool, *lines: str) -> "Container":
        """Add a text display only when ``condition`` is truthy."""
        if condition:
            self.text(*lines)
        return self

    def field(self, name: str, value: str) -> "Container":
        """Embed-field lookalike: bold name on one line, value below."""
        return self.text(f"**{name}**\n{value}")

    def field_if(self, condition: bool, name: str, value: str) -> "Container":
        """Add a field only when ``condition`` is truthy. Keeps chains clean."""
        if condition:
            self.field(name, value)
        return self

    def section(
        self,
        *lines: str,
        thumbnail: str | None = None,
        button: discord.ui.Button | None = None,
    ) -> "Container":
        """
        Add a section: up to 3 lines of text with one accessory on the right,
        either a ``thumbnail`` image URL or a ``button``.
        """
        accessory: discord.ui.Item
        if button is not None:
            accessory = button
        elif thumbnail:
            accessory = discord.ui.Thumbnail(thumbnail)
        else:
            # A section without an accessory is just text.
            return self.text(*lines)
        texts = [discord.ui.TextDisplay(self._clamp(t)) for t in lines[:3]]
        self._items.append(discord.ui.Section(*texts, accessory=accessory))
        return self

    def divider(self, *, visible: bool = True, large: bool = False) -> "Container":
        """Add a separator line (or just spacing when ``visible=False``)."""
        spacing = (
            discord.SeparatorSpacing.large if large else discord.SeparatorSpacing.small
        )
        self._items.append(discord.ui.Separator(visible=visible, spacing=spacing))
        return self

    def gallery(self, *urls: str) -> "Container":
        """Add a media gallery of 1-10 image URLs (or attachment:// refs)."""
        g = discord.ui.MediaGallery()
        for url in urls[:10]:
            g.add_item(media=url)
        self._items.append(g)
        return self

    def image(self, url: str) -> "Container":
        """Add a single full-width image (gallery of one)."""
        if url:
            self.gallery(url)
        return self

    def row(self, *items: discord.ui.Button | discord.ui.Select) -> "Container":
        """Add an action row of up to 5 buttons / 1 select."""
        self._items.append(discord.ui.ActionRow(*items))
        return self

    # ── Appearance ─────────────────────────────────────────────────────────

    def color(self, value: int) -> "Container":
        """Set the container accent color (use C_* constants from ui.py)."""
        self._color = value
        return self

    # ── Build ──────────────────────────────────────────────────────────────

    def to_item(self) -> discord.ui.Container:
        """Return the underlying ``discord.ui.Container`` item."""
        kwargs: dict = {"spoiler": self._spoiler}
        if self._color is not None:
            kwargs["accent_colour"] = discord.Colour(self._color)
        return discord.ui.Container(*self._items, **kwargs)

    def build(self, *, timeout: float | None = None) -> "V2View":
        """Wrap this container in a ready-to-send ``LayoutView``."""
        view = V2View(timeout=timeout)
        view.add_item(self.to_item())
        return view

    # ── Internal ───────────────────────────────────────────────────────────

    def _clamp(self, content: str) -> str:
        """Track and clamp total text size against the Discord 4000-char cap."""
        budget = _MAX_TEXT_TOTAL - self._text_total
        if len(content) > budget:
            log.warning(
                "components: text overflow, clamping",
                extra={"over_by": len(content) - budget},
            )
            content = content[: max(budget - 3, 0)] + "..."
        self._text_total += len(content)
        return content


class V2View(discord.ui.LayoutView):
    """
    Base ``LayoutView`` for Components V2 surfaces.

    Pass ``author_id`` to lock interactive components to one user (same
    behaviour as the framework's ``ConfirmView``); leave it ``None`` for
    static layouts with no interactive components.
    """

    def __init__(self, *, author_id: int | None = None, timeout: float | None = None) -> None:
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.message: discord.Message | None = None

    def add_container(self, container: Container) -> "V2View":
        """Attach a fluent ``Container`` builder to this view."""
        self.add_item(container.to_item())
        return self

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author_id is not None and interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This panel isn't yours.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.walk_children():
            if hasattr(child, "disabled"):
                child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


def _as_view(*containers: Container, view: V2View | None = None) -> V2View:
    """Collapse builders (and/or an explicit view) into one LayoutView."""
    out = view if view is not None else V2View()
    total = 0
    for c in containers:
        out.add_container(c)
        total += len(c._items) + 1
    if total > _MAX_COMPONENTS:
        log.warning(
            "components: component count over limit",
            extra={"count": total, "max": _MAX_COMPONENTS},
        )
    return out


async def send_v2(
    dest,
    *containers: Container,
    view: V2View | None = None,
    ephemeral: bool = False,
    **kwargs,
) -> discord.Message | None:
    """
    Send a Components V2 message.

    ``dest`` may be a command context, a channel, or an ``Interaction``
    (responds or follows up as appropriate). Components V2 messages cannot
    carry ``content`` or ``embeds`` -- put everything in the containers.
    """
    layout = _as_view(*containers, view=view)
    if isinstance(dest, discord.Interaction):
        if dest.response.is_done():
            msg = await dest.followup.send(view=layout, ephemeral=ephemeral, wait=True, **kwargs)
        else:
            await dest.response.send_message(view=layout, ephemeral=ephemeral, **kwargs)
            msg = await dest.original_response()
    else:
        msg = await dest.send(view=layout, **kwargs)
    layout.message = msg
    return msg


async def edit_v2(
    target,
    *containers: Container,
    view: V2View | None = None,
    **kwargs,
) -> discord.Message | None:
    """
    Edit a message (or interaction response) in place with a new V2 layout.

    ``target`` may be a ``discord.Message`` or an ``Interaction`` whose
    original response should be rewritten.
    """
    layout = _as_view(*containers, view=view)
    if isinstance(target, discord.Interaction):
        if target.response.is_done():
            msg = await target.edit_original_response(view=layout, **kwargs)
        else:
            await target.response.edit_message(view=layout, **kwargs)
            msg = await target.original_response()
    else:
        msg = await target.edit(view=layout, **kwargs)
    layout.message = msg
    return msg
