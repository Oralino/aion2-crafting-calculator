from pathlib import Path

import pytest

from aion2calc.data.aion2hub import Component, ParseError, RecipePage, parse_recipe_page

FIXTURES = Path(__file__).parent / "fixtures" / "aion2hub"


def parse(slug: str) -> RecipePage:
    html = (FIXTURES / f"{slug}.html").read_text(encoding="utf-8")
    return parse_recipe_page(html, int(slug.rsplit("-", 1)[1]))


def test_base_recipe_matches_game() -> None:
    page = parse("ruby-necklace-310160017")
    assert page == RecipePage(
        item_id=310160017,
        name="Ruby Necklace",
        grade="Common",
        profession="Jewelcrafting",
        mastery=10,
        components=(
            Component(610730021, "Ruby Decoration", 1),
            Component(610530001, "Refining Stone", 4),
            Component(610610013, "Odyle", 1),
        ),
    )


def test_combo_item_has_same_components_as_its_base_recipe() -> None:
    base = parse("ruby-necklace-310160017")
    combo = parse("splendent-ruby-necklace-310150010")
    assert combo.name == "Splendent Ruby Necklace"
    assert combo.grade == "Rare"
    assert combo.components == base.components


def test_next_tier_uses_the_combo_item() -> None:
    page = parse("expert-s-ruby-necklace-310150011")
    assert page.name == "Expert's Ruby Necklace"
    assert page.mastery == 25
    assert Component(310150010, "Splendent Ruby Necklace", 1) in page.components


def test_page_without_payload_is_rejected() -> None:
    with pytest.raises(ParseError):
        parse_recipe_page("<html></html>", 1)


def test_kr_tw_recipe_without_mastery() -> None:
    # This page has a length-prefixed text row (JSON-LD) directly followed by the title row.
    page = parse("noble-dragon-lord-longsword-110220021")
    assert page.name == "Noble Dragon Lord Longsword"
    assert page.grade == "Heroic"
    assert page.mastery is None
    assert page.kr_tw_only
    assert Component(930100030, "Kina (All)", 50_000_000) in page.components


def test_global_recipe_is_not_kr_tw_only() -> None:
    assert not parse("ruby-necklace-310160017").kr_tw_only
