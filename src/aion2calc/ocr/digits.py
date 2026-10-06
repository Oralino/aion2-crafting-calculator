"""Read market numbers (prices, listing counts) by matching digit glyphs.

The game draws numbers in one fixed font. General OCR misreads it with full confidence (`6999` →
`6669`, `999,990` → `066'666`), so numbers are read here instead: white glyphs are split by
column, the coin icon (taller than digits) is dropped, a short glyph between digits is a comma,
and each digit is matched against templates learned from known captures (ARCHITECTURE.md).
"""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PIL import Image

GLYPH_SIZE = (12, 18)  # width, height every digit is normalised to
DIGITS = "0123456789"
# Confidence limits, from reading each fixture capture with templates learned from the others:
# the best match was at most 0.14 away and at least 0.07 closer than the runner-up.
MAX_DISTANCE = 0.2
MIN_MARGIN = 0.03
TEMPLATES = Path(__file__).parent / "digit_templates.npz"

Glyph = NDArray[np.bool_]


@dataclass(frozen=True)
class Token:
    kind: str  # "d" (digit) or ","
    glyph: Glyph


def _white(cell: Image.Image) -> Glyph:
    a = np.asarray(cell.convert("RGB")).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    # Bright, unsaturated pixels: the number. The gold coin and dimmed (0-listing) rows fail this.
    return (r > 140) & (g > 140) & (b > 140) & (np.abs(r - b) < 40)


def _glyphs(cell: Image.Image) -> list[tuple[int, Glyph]]:
    """Connected runs of columns containing text, each trimmed to its rows."""
    mask = _white(cell)
    columns = mask.any(axis=0)
    out: list[tuple[int, Glyph]] = []
    x = 0
    while x < len(columns):
        if not columns[x]:
            x += 1
            continue
        start = x
        while x < len(columns) and columns[x]:
            x += 1
        glyph = mask[:, start:x]
        rows = np.flatnonzero(glyph.any(axis=1))
        out.append((start, glyph[rows[0] : rows[-1] + 1]))
    return out


def digit_height(cell: Image.Image) -> int | None:
    """Pixel height of the cell's digits (to spot a number cut off by the list's edge)."""
    digits = [t.glyph.shape[0] for t in tokens(cell) if t.kind == "d"]
    return max(set(digits), key=digits.count) if digits else None


def tokens(cell: Image.Image) -> list[Token]:
    """Digits (glyphs of the most common height) and commas (short glyphs between digits)."""
    glyphs = _glyphs(cell)
    heights = [g.shape[0] for _, g in glyphs if g.shape[0] > 6]
    if not heights:
        return []
    height = max(set(heights), key=heights.count)
    digit_x = [x for x, g in glyphs if abs(g.shape[0] - height) <= 2]
    first, last = digit_x[0], digit_x[-1]
    out = []
    for x, g in glyphs:
        if abs(g.shape[0] - height) <= 2:
            out.append(Token("d", g))
        elif first < x < last and g.shape[0] <= height * 0.4:
            out.append(Token(",", g))
    return out


def _normalise(glyph: Glyph) -> NDArray[np.float32]:
    image = Image.fromarray(glyph.astype(np.uint8) * 255).resize(
        GLYPH_SIZE, Image.Resampling.BILINEAR
    )
    return np.asarray(image, dtype=np.float32) / 255.0


@dataclass
class DigitTemplates:
    samples: dict[str, list[NDArray[np.float32]]] = field(default_factory=dict)

    def learn(self, cell: Image.Image, text: str) -> None:
        """Add the digits of a cell whose correct reading is `text` (commas optional)."""
        digits = [t for t in tokens(cell) if t.kind == "d"]
        expected = text.replace(",", "")
        if len(digits) != len(expected):
            raise ValueError(f"found {len(digits)} digits in the cell, expected {expected!r}")
        for token, digit in zip(digits, expected, strict=True):
            self.samples.setdefault(digit, []).append(_normalise(token.glyph))

    def read(self, cell: Image.Image) -> str:
        """The number in a cell as text (`"1,850,000"`), or "" when there's no readable number
        or any digit isn't a confident match (a wrong price is worse than none)."""
        text = ""
        for token in tokens(cell):
            if token.kind == ",":
                text += ","
                continue
            height, width = token.glyph.shape
            if width > height:
                return ""  # digits are taller than wide: touching digits or a stray line
            glyph = _normalise(token.glyph)
            distance = {
                d: min(float(np.abs(glyph - t).mean()) for t in samples)
                for d, samples in self.samples.items()
            }
            best, runner_up = sorted(distance.values())[:2]
            if best > MAX_DISTANCE or runner_up - best < MIN_MARGIN:
                return ""
            text += min(distance, key=distance.__getitem__)
        return text

    @property
    def complete(self) -> bool:
        return all(d in self.samples for d in DIGITS)

    def save(self, path: Path = TEMPLATES) -> None:
        arrays = {f"{d}_{i}": t for d, ts in self.samples.items() for i, t in enumerate(ts)}
        np.savez_compressed(path, **arrays)  # type: ignore[arg-type]

    @classmethod
    def load(cls, path: Path = TEMPLATES) -> "DigitTemplates":
        templates = cls()
        with np.load(path) as data:
            for key in sorted(data.files):
                templates.samples.setdefault(key.split("_")[0], []).append(data[key])
        if not templates.complete:
            missing = "".join(d for d in DIGITS if d not in templates.samples)
            raise ValueError(f"digit templates lack samples for {missing}")
        return templates


def parse_number(text: str) -> int | None:
    """A read number as an int; None for "" or a malformed reading. The game writes 10,000 and up
    with commas (4-digit numbers without), and never with a leading zero."""
    digits = text.replace(",", "")
    if not digits.isdigit() or (len(digits) > 1 and digits[0] == "0"):
        return None
    head, *rest = text.split(",")
    if rest and not (1 <= len(head) <= 3 and all(len(group) == 3 for group in rest)):
        return None
    if len(digits) > 4 and not rest:
        return None  # a dropped comma: the format check can't vouch for it
    return int(digits)
