from dataclasses import replace

import pytest

from aion2calc.data.aion2hub import Component, RecipePage
from aion2calc.data.recipes import Catalog, Ingredient, build_catalog

STONE = Component(1, "Refining Stone", 4)
FINE = Component(2, "Expert's Refining Stone", 4)
PURE = Component(3, "Artisan's Refining Stone", 4)


def page(item_id: int, name: str, grade: str, mastery: int, *parts: Component) -> RecipePage:
    return RecipePage(item_id, name, grade, "Jewelcrafting", mastery, parts)


# A three-tier necklace chain in two factions (ids 1xx and 2xx), like aion2hub lists it: every
# combo item has its own page repeating the recipe that combos into it.
PAGES = [
    page(110, "Ruby Necklace", "Common", 10, STONE),
    page(210, "Ruby Necklace", "Common", 10, STONE),
    page(111, "Splendent Ruby Necklace", "Rare", 10, STONE),
    page(211, "Splendent Ruby Necklace", "Rare", 10, STONE),
    page(120, "Expert's Ruby Necklace", "Rare", 25, Component(111, "Splendent", 1), FINE),
    page(220, "Expert's Ruby Necklace", "Rare", 25, Component(211, "Splendent", 1), FINE),
    page(121, "Expert's Splendent Ruby Necklace", "Epic", 25, Component(111, "Splendent", 1), FINE),
    page(221, "Expert's Splendent Ruby Necklace", "Epic", 25, Component(211, "Splendent", 1), FINE),
    page(130, "Artisan's Ruby Necklace", "Epic", 40, Component(121, "Expert's", 1), PURE),
]


def test_pairs_normal_and_combo_items_per_faction() -> None:
    catalog, warnings = build_catalog(PAGES)
    assert warnings == []
    assert catalog.recipes[110].combo_item_id == 111
    assert catalog.recipes[210].combo_item_id == 211
    assert catalog.recipes[120].combo_item_id == 121
    assert catalog.recipes[130].combo_item_id is None
    assert 111 not in catalog.recipes  # combo pages fold into their normal recipe


def test_chain_follows_combo_items_down() -> None:
    catalog, _ = build_catalog(PAGES)
    assert [r.item_id for r in catalog.chain(130)] == [110, 120, 130]
    assert [r.item_id for r in catalog.chain(220)] == [210, 220]


def test_items_include_components() -> None:
    catalog, _ = build_catalog(PAGES)
    assert catalog.name(1) == "Refining Stone"
    assert catalog.items[121].grade == "Epic"
    assert catalog.name(999) == "#999"


def test_ambiguous_group_is_reported_not_guessed() -> None:
    pages = [
        page(1, "A", "Common", 1, STONE),
        page(2, "B", "Rare", 1, STONE),
        page(3, "C", "Epic", 1, STONE),
    ]
    catalog, warnings = build_catalog(pages)
    assert len(warnings) == 1
    assert catalog.recipes[1].combo_item_id is None


def test_json_round_trip() -> None:
    catalog, _ = build_catalog(PAGES)
    loaded = Catalog.from_json(catalog.to_json())
    assert loaded.recipes == catalog.recipes
    assert loaded.items == catalog.items
    assert loaded.recipes[120].ingredients == (Ingredient(111, 1), Ingredient(2, 4))


def test_unknown_format_rejected() -> None:
    with pytest.raises(ValueError):
        Catalog.from_json('{"format": 99, "items": {}, "recipes": []}')


def test_unrelated_items_sharing_a_recipe_are_not_paired() -> None:
    pages = [page(1, "Iron Ring", "Common", 1, STONE), page(2, "Ruby Brooch", "Rare", 1, STONE)]
    catalog, warnings = build_catalog(pages)
    assert catalog.recipes[1].combo_item_id is None
    assert 2 in catalog.recipes  # kept as its own recipe
    assert len(warnings) == 1


def test_component_order_does_not_split_a_recipe() -> None:
    pages = [
        page(10, "Ruby Necklace", "Common", 10, STONE, FINE),
        page(11, "Splendent Ruby Necklace", "Rare", 10, FINE, STONE),
    ]
    catalog, warnings = build_catalog(pages)
    assert warnings == []
    assert catalog.recipes[10].combo_item_id == 11
    assert catalog.recipes[10].ingredients == (Ingredient(1, 4), Ingredient(2, 4))


def test_duplicate_pages_are_ignored() -> None:
    catalog, warnings = build_catalog([*PAGES, PAGES[0], PAGES[2]])
    assert warnings == []
    assert catalog.recipes[110].combo_item_id == 111


@pytest.mark.parametrize(
    ("grades", "problem"),
    [(("Common", "Shiny"), "unknown grade"), (("Common", "Rare", "Rare"), "uneven")],
)
def test_unpairable_groups_warn(grades: tuple[str, ...], problem: str) -> None:
    names = ["Ruby Necklace", "Splendent Ruby Necklace", "Splendent Ruby Necklace"]
    pages = [page(i, names[i], g, 1, STONE) for i, g in enumerate(grades)]
    catalog, warnings = build_catalog(pages)
    assert len(warnings) == 1 and problem in warnings[0]
    assert all(r.combo_item_id is None for r in catalog.recipes.values())


def test_kr_tw_only_needs_every_page_flagged() -> None:
    base = page(1, "Ruby Necklace", "Common", 1, STONE)
    combo = replace(page(2, "Splendent Ruby Necklace", "Rare", 1, STONE), kr_tw_only=True)
    catalog, _ = build_catalog([base, combo])
    assert not catalog.recipes[1].kr_tw_only
    catalog, _ = build_catalog([replace(base, kr_tw_only=True), combo])
    assert catalog.recipes[1].kr_tw_only


def test_chain_of_unknown_or_combo_item_explains() -> None:
    catalog, _ = build_catalog(PAGES)
    with pytest.raises(KeyError, match="no recipe makes"):
        catalog.chain(111)


def test_two_combo_ingredients_are_reported() -> None:
    pages = [
        *PAGES,
        page(140, "Odd Necklace", "Epic", 50, Component(111, "S", 1), Component(121, "E", 1)),
    ]
    _, warnings = build_catalog(pages)
    assert any("more than one combo item" in w for w in warnings)
