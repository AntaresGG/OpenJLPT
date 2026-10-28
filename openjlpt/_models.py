from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Literal, Optional

Level = Literal["N5", "N4", "N3", "N2", "N1"]
"""JLPT level in the current N5–N1 system."""


class _FrozenList(list):
    """List-compatible cached data: ordinary mutation is rejected."""

    def _immutable(self, *args, **kwargs):
        raise TypeError("OpenJLPT entries are read-only")

    __setitem__ = __delitem__ = __iadd__ = __imul__ = _immutable
    append = extend = insert = pop = remove = clear = reverse = sort = _immutable


class _FrozenDict(dict):
    def _immutable(self, *args, **kwargs):
        raise TypeError("OpenJLPT entries are read-only")

    __setitem__ = __delitem__ = __ior__ = _immutable
    update = setdefault = pop = popitem = clear = _immutable


def _freeze(value):
    if isinstance(value, list):
        return _FrozenList(_freeze(v) for v in value)
    if isinstance(value, dict):
        return _FrozenDict((k, _freeze(v)) for k, v in value.items())
    return value


class _ReadOnlyEntry:
    def __post_init__(self):
        for item in fields(self):
            object.__setattr__(self, item.name, _freeze(getattr(self, item.name)))


@dataclass(frozen=True)
class Example(_ReadOnlyEntry):
    """A Japanese↔English example sentence.

    Vocabulary examples come from Tatoeba (CC BY 2.0 FR) and carry ``tatoeba_id``
    (https://tatoeba.org/sentences/show/<id>); grammar examples are original.
    """

    ja: str
    en: str
    tatoeba_id: Optional[int] = None
    furigana: Optional[str] = None
    """``ja`` with readings over its kanji in ``{漢字|かんじ}`` notation, when every kanji
    could be read with confidence (see :func:`openjlpt.to_ruby_html`)."""


@dataclass(frozen=True)
class Vocab(_ReadOnlyEntry):
    """A single JLPT vocabulary entry."""

    id: str
    """Stable ID (10 hex digits), assigned once and kept across data updates."""
    word: str
    reading: str
    """Kana reading (equals ``word`` for kana-only words)."""
    romaji: str
    """Hepburn romanization of ``reading``, without macrons."""
    meanings: List[str]
    level: Level
    pos: List[str] = field(default_factory=list)
    """JMdict part-of-speech codes (see :func:`openjlpt.pos_labels`)."""
    jmdict_id: Optional[int] = None
    other_forms: List[str] = field(default_factory=list)
    other_readings: List[str] = field(default_factory=list)
    examples: List[Example] = field(default_factory=list)

    zh: Optional[Dict[str, Any]] = None

    def __hash__(self) -> int:  # list fields aren't hashable; the ID identifies the entry
        return hash(("vocab", self.id))


@dataclass(frozen=True)
class Kanji(_ReadOnlyEntry):
    """A single JLPT kanji, enriched from KANJIDIC2."""

    character: str
    level: Level
    strokes: Optional[int]
    grade: Optional[int]
    freq: Optional[int]
    radical: Optional[str]
    """Classical (Kangxi) radical, e.g. 日."""
    radical_number: Optional[int]
    onyomi: List[str]
    kunyomi: List[str]
    meanings: List[str]
    nanori: List[str] = field(default_factory=list)
    words: List[str] = field(default_factory=list)
    """OpenJLPT words that use this kanji, easiest level first."""
    supplementary: bool = False
    """A jōyō kanji missing from Waller's (pre-2010) lists, levelled by the words that use it."""

    def __hash__(self) -> int:
        return hash(("kanji", self.character))


@dataclass(frozen=True)
class Grammar(_ReadOnlyEntry):
    """A single JLPT grammar point."""

    id: str
    """Stable ID, a slug of the romaji (e.g. ``te-mo-ii``)."""
    pattern: str
    romaji: str
    level: Level
    meaning: str
    formation: str
    examples: List[Example] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    reading: Optional[str] = None
    """Kana form of ``pattern`` when it contains kanji."""
    notes: Optional[str] = None

    zh: Optional[Dict[str, Any]] = None

    def __hash__(self) -> int:
        return hash(("grammar", self.id))
