"""Tests for core/framework/components.py  -  Components V2 DSL."""
from __future__ import annotations

import discord
import pytest

from core.framework.components import Container, V2View, _MAX_TEXT_TOTAL
from constants.ui import C_INFO


class TestContainerBuilder:
    def test_text_adds_text_display(self):
        view = Container().text("hello").build()
        container = view.children[0]
        assert isinstance(container, discord.ui.Container)
        assert isinstance(container.children[0], discord.ui.TextDisplay)
        assert container.children[0].content == "hello"

    def test_text_joins_lines(self):
        view = Container().text("a", "b").build()
        assert view.children[0].children[0].content == "a\nb"

    def test_field_formats_name_and_value(self):
        view = Container().field("Balance", "$5.00").build()
        assert view.children[0].children[0].content == "**Balance**\n$5.00"

    def test_field_if_false_skips(self):
        view = Container().field_if(False, "K", "V").build()
        assert len(view.children[0].children) == 0

    def test_color_sets_accent(self):
        view = Container(color=C_INFO).text("x").build()
        assert view.children[0].accent_colour == discord.Colour(C_INFO)

    def test_divider_adds_separator(self):
        view = Container().text("a").divider().text("b").build()
        assert isinstance(view.children[0].children[1], discord.ui.Separator)

    def test_section_with_button_accessory(self):
        btn = discord.ui.Button(label="Go")
        view = Container().section("line", button=btn).build()
        section = view.children[0].children[0]
        assert isinstance(section, discord.ui.Section)
        assert section.accessory is btn

    def test_section_without_accessory_is_text(self):
        view = Container().section("just text").build()
        assert isinstance(view.children[0].children[0], discord.ui.TextDisplay)

    def test_row_adds_action_row(self):
        btn = discord.ui.Button(label="A")
        view = Container().row(btn).build()
        assert isinstance(view.children[0].children[0], discord.ui.ActionRow)

    def test_gallery_caps_at_ten(self):
        urls = [f"https://example.com/{i}.png" for i in range(12)]
        view = Container().gallery(*urls).build()
        gallery = view.children[0].children[0]
        assert isinstance(gallery, discord.ui.MediaGallery)
        assert len(gallery.items) == 10

    def test_text_overflow_is_clamped(self):
        view = Container().text("x" * (_MAX_TEXT_TOTAL + 500)).build()
        content = view.children[0].children[0].content
        assert len(content) <= _MAX_TEXT_TOTAL
        assert content.endswith("...")

    def test_chaining_returns_self(self):
        c = Container()
        assert c.text("a").divider().field("k", "v") is c


class TestV2View:
    def test_author_lock_default_none(self):
        view = V2View()
        assert view.author_id is None

    def test_add_container(self):
        view = V2View(author_id=123)
        view.add_container(Container().text("hi"))
        assert isinstance(view.children[0], discord.ui.Container)

    @pytest.mark.asyncio
    async def test_interaction_check_allows_author(self):
        view = V2View(author_id=42)

        class _User:
            id = 42

        class _Interaction:
            user = _User()

        assert await view.interaction_check(_Interaction())
