"""Recipe catalog: normal recipes paired with their combo items, and tier chains between them.

aion2hub has a page per craftable item, including combo items (e.g. "Splendent Ruby Necklace"),
whose page repeats the recipe that can combo into it. Pages with the same profession, mastery and
components are one recipe. Within it, a combo item's name keeps every word of its normal item's
name and adds some ("Splendent ..."); grade is only a sanity check, because the top tier's normal
and combo items share a grade (both Star Dragon Lord Necklaces are Unique). Each faction has its own
item ids for the same recipe, so a group can hold two of each; they are paired in id order.

A tier chain follows combo items downwards: a recipe that uses a combo item as a component is the
next tier of the recipe that combos into it (Star Dragon Lord ← Artisan's ← Expert's ← base).
"""

import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path

from aion2calc.data.aion2hub import RecipePage

GRADES = ("Common", "Rare", "Epic", "Unique")
"""Global grades, lowest first (owner, 2026-10-05). KR/TW data also has "Heroic", whose rank isn't
known; groups with any other grade are reported, not paired."""

FORMAT_VERSION = 1


@dataclass(frozen=True)
class Ingredient:
    item_id: int
    qty: int


@dataclass(frozen=True)
class Recipe:
    item_id: int
    """The normal result."""
    profession: str
    mastery: int | None
    ingredients: tuple[Ingredient, ...]
    combo_item_id: int | None = None
    """The item a combo produces instead, if the recipe has one."""
    kr_tw_only: bool = False
    """Only known from Korea/Taiwan client data; may not exist on Global."""


@dataclass(frozen=True)
class Item:
    name: str
    grade: str | None = None
    """Known only for crafted items."""


def _words(name: str) -> set[str]:
    return set(name.lower().split())


def _is_combo_name(normal: str, combo: str) -> bool:
    """A combo item's name keeps every word of the normal one ("Expert's Splendent Ruby Necklace"
    for "Expert's Ruby Necklace"), so unrelated items that share a recipe aren't paired."""
    return normal != combo and _words(normal) <= _words(combo)


class Catalog:
    def __init__(self, items: dict[int, Item], recipes: Iterable[Recipe]) -> None:
        self.items = items
        self.recipes = {r.item_id: r for r in recipes}
        self._by_combo = {r.combo_item_id: r for r in self.recipes.values() if r.combo_item_id}

    def name(self, item_id: int) -> str:
        item = self.items.get(item_id)
        return item.name if item else f"#{item_id}"

    def chain(self, item_id: int) -> tuple[Recipe, ...]:
        """Tiers that end in `item_id`'s recipe, lowest tier first."""
        if item_id not in self.recipes:
            raise KeyError(
                f"no recipe makes {self.name(item_id)} (a combo item's recipe is "
                "listed under its normal item)"
            )
        tiers = [self.recipes[item_id]]
        while lower := self._lower_tier(tiers[0]):
            if lower in tiers:
                raise ValueError(f"recipe cycle at {self.name(lower.item_id)}")
            tiers.insert(0, lower)
        return tuple(tiers)

    def _lower_tier(self, recipe: Recipe) -> Recipe | None:
        lower = [
            self._by_combo[i.item_id] for i in recipe.ingredients if i.item_id in self._by_combo
        ]
        if len(lower) > 1:
            raise ValueError(f"{self.name(recipe.item_id)} uses more than one combo item")
        return lower[0] if lower else None

    def to_json(self) -> str:
        data = {
            "format": FORMAT_VERSION,
            "items": {
                str(i): {"name": item.name, "grade": item.grade}
                for i, item in sorted(self.items.items())
            },
            "recipes": [
                {
                    "item": r.item_id,
                    "profession": r.profession,
                    "mastery": r.mastery,
                    "ingredients": [[i.item_id, i.qty] for i in r.ingredients],
                    "combo": r.combo_item_id,
                    "kr_tw_only": r.kr_tw_only,
                }
                for r in sorted(self.recipes.values(), key=lambda r: r.item_id)
            ],
        }
        return json.dumps(data, ensure_ascii=False, indent=1) + "\n"

    @classmethod
    def from_json(cls, text: str) -> "Catalog":
        data = json.loads(text)
        if data.get("format") != FORMAT_VERSION:
            raise ValueError(f"unsupported recipe data format {data.get('format')!r}")
        items = {int(i): Item(v["name"], v["grade"]) for i, v in data["items"].items()}
        recipes = [
            Recipe(
                r["item"],
                r["profession"],
                r["mastery"],
                tuple(Ingredient(i, q) for i, q in r["ingredients"]),
                r["combo"],
                r["kr_tw_only"],
            )
            for r in data["recipes"]
        ]
        return cls(items, recipes)

    @classmethod
    def load(cls, path: Path) -> "Catalog":
        return cls.from_json(path.read_text(encoding="utf-8"))


def searchable_recipes(catalog: Catalog, include_kr_tw: bool = False) -> dict[str, int]:
    """Recipe picker entries, "Name · Grade" → item id, sorted by name. Faction copies of a recipe
    share a name, so each name appears once (lowest id). KR/TW-only recipes are left out unless
    asked for."""
    entries: dict[str, int] = {}
    for item_id in sorted(catalog.recipes):
        if catalog.recipes[item_id].kr_tw_only and not include_kr_tw:
            continue
        item = catalog.items.get(item_id)
        name = catalog.name(item_id)
        entries.setdefault(f"{name} · {item.grade}" if item and item.grade else name, item_id)
    return dict(sorted(entries.items(), key=lambda entry: entry[0].lower()))


def build_catalog(pages: Iterable[RecipePage]) -> tuple[Catalog, list[str]]:
    """Group pages into recipes. Returns the catalog and warnings about anything it couldn't pair.

    When a group can't be paired safely, every page in it is kept as its own recipe without a combo,
    rather than guessing."""
    items: dict[int, Item] = {}
    groups: dict[tuple[str, int | None, tuple[tuple[int, int], ...]], dict[int, RecipePage]]
    groups = defaultdict(dict)
    for page in pages:
        items[page.item_id] = Item(page.name, page.grade)
        for c in page.components:
            items.setdefault(c.item_id, Item(c.name))
        # Sorted, so a page listing the same components in another order still groups.
        components = tuple(sorted((c.item_id, c.qty) for c in page.components))
        groups[(page.profession, page.mastery, components)][page.item_id] = page  # dedupes

    recipes: list[Recipe] = []
    warnings: list[str] = []
    for (profession, mastery, _), by_id in groups.items():
        group = list(by_id.values())
        # Keep the page's own component order for display.
        ingredients = tuple(Ingredient(c.item_id, c.qty) for c in group[0].components)
        kr_tw_only = all(p.kr_tw_only for p in group)
        pairs, problem = _pair(group)
        if problem and not kr_tw_only:  # KR/TW-only data has grades Global doesn't (Heroic)
            names = ", ".join(sorted({p.name for p in group}))
            warnings.append(f"{problem} ({names}); combo items left out")
        for normal, combo in pairs:
            recipes.append(Recipe(normal, profession, mastery, ingredients, combo, kr_tw_only))

    recipes = _pair_splendent_by_name(recipes, items)
    catalog = Catalog(items, recipes)
    for recipe in catalog.recipes.values():
        try:
            catalog.chain(recipe.item_id)
        except ValueError as error:
            warnings.append(str(error))
    return catalog, warnings


def _pair(group: list[RecipePage]) -> tuple[list[tuple[int, int | None]], str | None]:
    """Pair a recipe group's normal items with their combo items (one pair per faction)."""
    alone: list[tuple[int, int | None]] = [(p.item_id, None) for p in sorted(group, key=_id)]
    names = _by_name(group)
    grade = {p.name: p.grade for p in group}
    combo_names = {c for c in names if any(_is_combo_name(n, c) for n in names)}
    if not combo_names:
        if len(set(grade.values())) > 1:
            return alone, "different items share a recipe"
        return alone, None  # one item (per faction), or several items sharing a recipe
    if unknown := set(grade.values()) - set(GRADES):
        return alone, f"unknown grade {', '.join(sorted(unknown))}"
    # Several items can share one recipe (e.g. Orichalcum Dagger, Mace, ...), so match by name.
    matches = {
        n: [c for c in combo_names if _is_combo_name(n, c)] for n in names if n not in combo_names
    }
    matched = [found[0] for found in matches.values() if len(found) == 1]
    if any(len(found) != 1 for found in matches.values()) or sorted(matched) != sorted(combo_names):
        return alone, "combo names don't match one-to-one"
    pairs: list[tuple[int, int | None]] = []
    for name, (combo_name,) in matches.items():
        if GRADES.index(grade[combo_name]) < GRADES.index(grade[name]):
            return alone, "combo item has a lower grade"
        if len(names[name]) != len(names[combo_name]):
            return alone, "uneven normal and combo items"
        # Each faction has its own ids; they're numbered in the same order for both items.
        pairs += zip(names[name], names[combo_name], strict=True)
    return sorted(pairs), None


def _pair_splendent_by_name(recipes: list[Recipe], items: dict[int, Item]) -> list[Recipe]:
    """Second pass: aion2hub lists some top-tier Splendent items (e.g. Splendent Dark Dragon Lord
    Boots) with a different, smaller recipe than their normal item, so the component match misses
    them. In game they're the normal recipe's 25% combo result (owner, 2026-10-05), so pair
    "Splendent <name>" with "<name>" by name, per faction in id order, and drop its own recipe."""
    unpaired: dict[str, list[Recipe]] = defaultdict(list)
    for recipe in sorted(recipes, key=lambda r: r.item_id):
        if recipe.combo_item_id is None:
            unpaired[items[recipe.item_id].name].append(recipe)
    combos: dict[int, int] = {}
    for name, normal in unpaired.items():
        splendent = unpaired.get(f"Splendent {name}", [])
        if not splendent or len(splendent) != len(normal):
            continue
        n_grade, s_grade = items[normal[0].item_id].grade, items[splendent[0].item_id].grade
        same_job = {r.profession for r in normal + splendent} == {normal[0].profession}
        if not same_job or n_grade not in GRADES or s_grade not in GRADES:
            continue
        if GRADES.index(s_grade) < GRADES.index(n_grade):
            continue
        combos.update((n.item_id, c.item_id) for n, c in zip(normal, splendent, strict=True))
    dropped = set(combos.values())
    return [
        replace(r, combo_item_id=combos[r.item_id]) if r.item_id in combos else r
        for r in recipes
        if r.item_id not in dropped
    ]


def _by_name(pages: Iterable[RecipePage]) -> dict[str, list[int]]:
    """Item ids per name, in id order."""
    names: dict[str, list[int]] = defaultdict(list)
    for page in sorted(pages, key=_id):
        names[page.name].append(page.item_id)
    return names


def _id(page: RecipePage) -> int:
    return page.item_id
