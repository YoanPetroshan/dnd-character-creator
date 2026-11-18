"""S3: every option of every i18n-zoo resolution either carries a `description` or sits on the explicit allowlist
`TEXTLESS_CARDS` (skills, tools, languages, abilities, sizes, spells, weapons, equipment, damage types ...: options whose
label IS the whole content or whose text the UI fetches lazily). A NEW kind of option card without text fails here: give it
a description or (when its label says it all) add its card id pattern to the allowlist, on purpose.
Also pins the S3 texts: species lineages, Circle of the Land, Elemental Affinity, Primal Companion, Feywild Gifts."""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import i18n_zoo  # noqa: E402
from catalog.loader import load  # noqa: E402
from catalog.official_source import has_official, has_official_classes  # noqa: E402
from engine.resolve import resolve  # noqa: E402
from i18n.messages import localize, validate_catalog  # noqa: E402

pytestmark = pytest.mark.skipif(bool(i18n_zoo.NEEDS_DATA), reason="needs the official data")

_ID = r"[^:]+"
# regexes over the CARD id (fullmatch); every one names a kind of card whose options are plain picks
TEXTLESS_CARDS = [
    rf"background:{_ID}:(ability-bonus|equipment-choice-\d+(:\d+)?|feat-\d+|languages|proficiency-choice-\d+)",
    rf"class:{_ID}:\d+:asi(:feat:.+)?",                              # ability picks, and the sub-picks of a feat taken at an ASI
    rf"class:{_ID}:\d+:(enemy-type|terrain-type):.+",                 # Favored Enemy / Natural Explorer picks
    rf"class:{_ID}:\d+:equipment-choice-\d+(:\d+)?",
    rf"class:{_ID}:\d+:expertise-choice:.+",
    rf"class:{_ID}:\d+:feature:.+",                                   # skills, tools and spells of feature picks (checked below)
    rf"class:{_ID}:\d+:languages:.+",
    rf"class:{_ID}:\d+:(mystic-arcanum-\d+|prof-choice-\d+|signature-spells|spell-mastery-\d+|tool-choice:.+)",
    rf"class:{_ID}:invocation:.+",                                    # cantrips, weapons, feats and rituals chosen for an invocation
    rf"class:{_ID}:(multiclass-prof-choice-\d+|spellbook|spells-cantrips|spells-known|weapon-mastery)",
    r"feat:.+:(spell-ability|spell-choice-\d+|spell-variant)",
    r"origin:languages",
    rf"species:{_ID}:(ability-bonus|draconic-ancestry|feat-\d+(:feat:.+)?|innate-cantrip|languages|resistance|size|spell-ability)",
    rf"species:{_ID}:trait:.+",                                       # Draconic Ancestry colour, tool and skill picks of a trait
]
# feature picks that are only skills / spells / tools (the label is the content)
TEXTLESS_FEATURES = {"abjurer-xphb-3-abjuration-savant", "additional-magical-secrets", "battle-master-xphb-3-student-of-war",
                     "bonus-proficiencies", "evoker-xphb-3-evocation-savant", "fey-wanderer-xphb-3-otherworldly-glamour",
                     "xphb-barbarian-3-primal-knowledge"}


def _allowed(card_id: str) -> bool:
    if not any(re.fullmatch(p, card_id) for p in TEXTLESS_CARDS):
        return False
    m = re.fullmatch(rf"class:{_ID}:\d+:feature:(.+)", card_id)
    return m is None or m.group(1) in TEXTLESS_FEATURES or "savant" in m.group(1)


def test_every_zoo_option_has_text_or_is_allowlisted():
    cat = load()
    bad: dict[str, str] = {}
    for name, draft in sorted(i18n_zoo.zoo(cat).items()):
        res = resolve(json.loads(json.dumps(draft)), i18n_zoo.catalog_for(name, cat))
        for card in res["choices"]:
            for option in card.get("options") or []:
                if not option.get("description") and not _allowed(card["id"]):
                    bad.setdefault(re.sub(r"\d+", "N", card["id"]), f"{name}: {card['id']} / {option['id']}")
    assert not bad, "options without a description on no allowlisted card:\n" + "\n".join(sorted(bad.values()))


def _draft(species, cls, sub, level):
    d = copy.deepcopy(i18n_zoo.base())
    d["ruleset"], d["sources"] = "2024", []
    d["species"] = {"id": species, "choices": {}}
    d["classes"] = [{"classId": cls, "level": level, "subclassId": sub, "choices": {}}]
    return d


def _options(res, suffix):
    card = next(c for c in res["choices"] if c["id"].endswith(suffix))
    return {o["id"].split("--")[-1]: o.get("description") for o in card["options"]}


@pytest.mark.skipif(not (has_official() and has_official_classes()), reason="official data missing")
def test_s3_texts_en_and_bg():
    cat = load()
    res = resolve(_draft("elf-xphb", "druid", "land-xphb", 3), cat)
    bg = localize(res, "bg")
    land = _options(res, "circle-of-the-land-spells")
    assert land["arid"].startswith("Spells always prepared: Druid level 3: Blur, Burning Hands, Fire Bolt; Druid level 5: Fireball")
    assert _options(bg, "circle-of-the-land-spells")["arid"].startswith("Винаги подготвени заклинания: Ниво 3 на друида: Blur")
    drow = _options(res, ":variant")["drow-lineage"]
    assert drow.startswith("Darkvision 120 feet; Spells: Dancing Lights (level 1), Faerie Fire (level 3), Darkness (level 5).\nYou are part of a lineage")
    assert _options(bg, ":variant")["drow-lineage"].startswith("Тъмно зрение (Darkvision) 120 фута (36 м); Заклинания: Dancing Lights (ниво 1)")
    wood = _options(bg, ":variant")["wood-elf-lineage"]
    assert wood.startswith("Скорост 35 фута (10,5 м);")
    res = resolve(_draft("goliath-xphb", "ranger", "beast-master-xphb", 3), cat)
    assert _options(res, ":variant")["cloud-giant-ancestry"].startswith("Cloud's Jaunt. As a Bonus Action")  # no structured fields: text only
    companion = _options(res, "primal-companion")
    assert set(companion) == {"beast-of-the-land", "beast-of-the-sea", "beast-of-the-sky"}
    assert all(t.startswith("Summary (not the full stat block)") for t in companion.values())
    assert _options(localize(res, "bg"), "primal-companion")["beast-of-the-sea"].startswith("Резюме (не е пълното описание")
    res = resolve(_draft("dragonborn-xphb", "sorcerer", "draconic-xphb", 6), cat)
    assert _options(res, ":variant")["dragonborn-black"] == "Resistance to acid damage."
    assert _options(localize(res, "bg"), ":variant")["dragonborn-black"] == "Устойчивост (Resistance) към щети от киселина (Acid)."
    aff = _options(res, "elemental-affinity")
    assert set(aff) == {"acid", "cold", "fire", "lightning", "poison"} and "Resistance to fire damage" in aff["fire"]
    res = resolve(_draft("human-xphb", "ranger", "fey-wanderer-xphb", 3), cat)
    gifts = _options(res, "fey-wanderer-spells")
    assert len(gifts) == 6 and gifts["gift-5"] == "Horns or antlers sprout from your head."


def test_every_variant_carries_a_text_field():
    """`variants[].text` is new (book paragraphs, "" when the data has none); trait `desc` stays as it was, so the species
    overlay hashes (and the 169 translated species) stay fresh."""
    cat = load()
    variants = [v for r in cat.races.values() for v in r.get("variants") or []]
    assert variants and all(isinstance(v.get("text"), str) for v in variants)


def test_option_text_messages_are_well_formed():
    assert validate_catalog(require_bg=True) == []
