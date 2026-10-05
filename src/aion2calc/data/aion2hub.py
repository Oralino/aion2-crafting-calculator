"""Parse aion2hub.com crafting-calculator pages (Next.js React Server Components payload).

The page HTML embeds its content as `self.__next_f.push([1, "<chunk>"])` scripts. Joined, the
chunks form rows of `<hex id>:<json>`; elements are `["$", tag, key, props]` and `"$L<id>"` strings
refer to other rows. We walk that tree instead of the rendered HTML, which isn't fully sent.
"""

import json
import re
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

_CHUNK = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', re.S)
_ROW = re.compile(rb"([0-9a-f]*):")  # hint rows (`:HL[...]`) have no id
_TEXT_ROW = re.compile(rb"T([0-9a-f]+),")
_ITEM_HREF = re.compile(r"^/database/items/(\d+)$")
_DIRECT_HEADING = "recipe — direct components"


@dataclass(frozen=True)
class Component:
    item_id: int
    name: str
    qty: int


@dataclass(frozen=True)
class RecipePage:
    item_id: int
    name: str
    grade: str
    profession: str
    mastery: int | None
    """Required crafting mastery; some recipes (e.g. Abyss gear) don't list one."""
    components: tuple[Component, ...]
    kr_tw_only: bool = False
    """aion2hub marks recipes only known from Korea/Taiwan client data with a "KR/TW" badge."""


class ParseError(ValueError):
    pass


def _payload(html: str) -> str:
    chunks = _CHUNK.findall(html)
    if not chunks:
        raise ParseError("no Next.js payload in page")
    return "".join(json.loads(f'"{chunk}"') for chunk in chunks)


def _rows(payload: str) -> dict[str, Any]:
    """Split the payload into rows. Most rows end at a newline, but text rows (`<id>:T<hex len>,`)
    are length-prefixed in UTF-8 bytes and the next row follows them directly."""
    data = payload.encode("utf-8")
    rows: dict[str, Any] = {}
    pos = 0
    while pos < len(data):
        if data[pos : pos + 1] == b"\n":
            pos += 1
            continue
        match = _ROW.match(data, pos)
        if match is None:
            raise ParseError(f"unexpected payload at byte {pos}")
        start = match.end()
        if (text := _TEXT_ROW.match(data, start)) is not None:
            pos = text.end() + int(text.group(1), 16)
            if pos > len(data):
                raise ParseError("text row runs past the end of the payload")
            continue  # text rows hold JSON-LD and similar; we don't need them
        end = data.find(b"\n", start)
        end = len(data) if end < 0 else end
        body = data[start:end].decode("utf-8")
        # Module and hint rows aren't JSON; we don't need them.
        with suppress(json.JSONDecodeError):
            if body[:1] in "[{":
                rows[match.group(1).decode()] = json.loads(body)
        pos = end + 1
    return rows


class _Tree:
    def __init__(self, rows: dict[str, Any]) -> None:
        self._rows = rows

    def resolve(self, node: Any) -> Any:
        if isinstance(node, str) and node.startswith("$L") and node[2:] in self._rows:
            return self._rows[node[2:]]
        return node

    def text(self, node: Any, depth: int = 0) -> str:
        """All text inside a node, references resolved."""
        if depth > 200:
            raise ParseError("element tree too deep (reference cycle?)")
        node = self.resolve(node)
        if isinstance(node, str):
            return "" if node.startswith("$") else node
        if isinstance(node, int | float) and not isinstance(node, bool):
            return str(node)
        if _is_element(node):
            return self.text(node[3].get("children"), depth + 1)
        if isinstance(node, list):
            return "".join(self.text(child, depth + 1) for child in node)
        return ""

    def walk(self, node: Any) -> Any:
        """Yield every element (depth first) and the list it sits in."""
        stack = [self.resolve(node)]
        seen: set[int] = set()
        while stack:
            current = stack.pop()
            if id(current) in seen:
                continue
            seen.add(id(current))
            if _is_element(current):
                yield current
                stack.append(self.resolve(current[3].get("children")))
            elif isinstance(current, list):
                stack.extend(self.resolve(child) for child in reversed(current))


def _is_element(node: Any) -> bool:
    return (
        isinstance(node, list)
        and len(node) == 4
        and node[0] == "$"
        and isinstance(node[1], str)
        and isinstance(node[3], dict)
    )


def _labelled(tree: _Tree, root: Any, label: str) -> str | None:
    """Value of a `<span>Label: <span>value</span></span>` chip."""
    for element in tree.walk(root):
        children = element[3].get("children")
        if isinstance(children, list) and children and children[0] == label:
            return tree.text(children[1:]).strip()
    return None


def _required(value: str | None, label: str) -> str:
    if not value:
        raise ParseError(f"no {label!r} on page")
    return value


def _components(tree: _Tree, root: Any) -> tuple[Component, ...]:
    for element in tree.walk(root):
        if element[1] != "div":
            continue
        children = tree.resolve(element[3].get("children"))
        if not isinstance(children, list) or len(children) < 2:
            continue
        heading = tree.resolve(children[0])
        if _is_element(heading) and heading[1] == "h2" and _DIRECT_HEADING in tree.text(heading):
            components = tuple(
                _component(tree, li) for li in tree.walk(children[1]) if li[1] == "li"
            )
            if not components:
                raise ParseError("empty component list")
            return components
    raise ParseError("no direct components on page")


def _component(tree: _Tree, li: Any) -> Component:
    item_id = name = None
    qty_text = ""
    for element in tree.walk(li):
        href = element[3].get("href")
        if name is None and isinstance(href, str) and (match := _ITEM_HREF.match(href)):
            item_id, name = int(match.group(1)), tree.text(element).strip() or None
        elif "tabular-nums" in element[3].get("className", ""):
            qty_text = tree.text(element)
    qty = re.sub(r"\D", "", qty_text)
    if item_id is None or not name or not qty:
        raise ParseError(f"incomplete component: {tree.text(li)!r}")
    return Component(item_id, name, int(qty))


def _header(tree: _Tree, root: Any) -> Any:
    """The chip row holding Grade/Profession/Mastery (and the KR/TW badge, if any)."""
    for element in tree.walk(root):
        children = tree.resolve(element[3].get("children"))
        if isinstance(children, list) and any(
            _is_element(c) and tree.resolve(c[3].get("children", [None]))[:1] == ["Grade: "]
            for c in map(tree.resolve, children)
        ):
            return element
    raise ParseError("no grade chip on page")


def parse_recipe_page(html: str, item_id: int) -> RecipePage:
    """Parse one `/tools/crafting-calculator/<slug>-<item_id>` page. Any failure is a ParseError."""
    try:
        return _parse(html, item_id)
    except ParseError:
        raise
    except (ValueError, LookupError, TypeError, RecursionError) as error:
        raise ParseError(f"{type(error).__name__}: {error}") from error


def _parse(html: str, item_id: int) -> RecipePage:
    rows = _rows(_payload(html))
    tree = _Tree(rows)
    root = list(rows.values())
    # The layout also carries a hidden "404" h1, so match the recipe title's " — " suffix.
    titles = (tree.text(e) for e in tree.walk(root) if e[1] == "h1")
    name = next((t.split(" — ")[0].strip() for t in titles if " — " in t), "")
    if not name:
        raise ParseError("no recipe name on page")
    header = _header(tree, root)
    mastery = _labelled(tree, header, "Mastery level: ")
    return RecipePage(
        item_id=item_id,
        name=name,
        grade=_required(_labelled(tree, header, "Grade: "), "Grade: "),
        profession=_required(_labelled(tree, header, "Profession: "), "Profession: "),
        mastery=int(mastery) if mastery else None,
        components=_components(tree, root),
        kr_tw_only=any(e[3].get("children") == "KR/TW" for e in tree.walk(header)),
    )
