"""S3: the generated option descriptions (species lineage / ancestry summaries, Circle of the Land spell lists, Elemental
Affinity, the Primal Companion summaries). English is the engine's own wording (structured data or our own words, never the
book's text); the Bulgarian follows docs/TRANSLATION-STYLE-BG.md: "ти", the term bracket at first use, feet with metres,
damage as "щети от X (Type)", ability names English.

A distance is `{n} feet{m:.0s}`: the English template swallows the metres (`m`, a string such as "10,5"), the Bulgarian
shows them ("35 фута (10,5 м)"), so both templates use the same parameter names.
"""
from __future__ import annotations

_DTYPES = {
    "acid": "киселина (Acid)", "bludgeoning": "удар (Bludgeoning)", "cold": "студ (Cold)", "fire": "огън (Fire)",
    "force": "силова енергия (Force)", "lightning": "мълния (Lightning)", "necrotic": "некротична енергия (Necrotic)",
    "piercing": "пробождане (Piercing)", "poison": "отрова (Poison)", "psychic": "психична енергия (Psychic)",
    "radiant": "сияйна енергия (Radiant)", "slashing": "рязане (Slashing)", "thunder": "гръм (Thunder)",
}

MESSAGES: dict[str, dict[str, str]] = {
    "opt-variant": {"en": "{summary}\n{text}", "bg": "{summary}\n{text}"},
    "opt-summary": {"en": "{parts:; }.", "bg": "{parts:; }."},
    "opt-speed": {"en": "Speed {n} feet{m:.0s}", "bg": "Скорост {n} фута ({m} м)"},
    "opt-darkvision": {"en": "Darkvision {n} feet{m:.0s}", "bg": "Тъмно зрение (Darkvision) {n} фута ({m} м)"},
    "opt-resist": {"en": "Resistance to {types:, } damage", "bg": "Устойчивост (Resistance) към щети от {types:, }"},
    "opt-spells": {"en": "Spells: {spells:, }", "bg": "Заклинания: {spells:, }"},
    "opt-spell": {"en": "{name} (level {level})", "bg": "{name} (ниво {level})"},
    "opt-affinity": {
        "en": "You have Resistance to {dtype} damage, and a spell of yours that deals {dtype} damage gets your "
              "Charisma modifier added to one of its damage rolls.",
        "bg": "Имаш устойчивост (Resistance) към щети от {dtype}, а когато заклинание, което нанася такива щети, "
              "се хвърля от теб, добавяш модификатора на Charisma към едно от хвърлянията му за щети.",
    },
    "opt-land": {"en": "Spells always prepared: {levels:; }.", "bg": "Винаги подготвени заклинания: {levels:; }."},
    "opt-land-level": {"en": "Druid level {level}: {names:, }", "bg": "Ниво {level} на друида: {names:, }"},
    "opt-companion-land": {
        "en": "Summary (not the full stat block): a Medium beast built for the ground, with a Speed of 40 feet and a "
              "Climb Speed of 40 feet. Its signature trait, Charge, lets it dash at a foe and hit harder after a "
              "straight run.",
        "bg": "Резюме (не пълният блок с характеристики): звяр със среден размер, създаден за сушата, със "
              "скорост 40 фута (12 м) и скорост на катерене 40 фута (12 м). Особеното му умение, "
              "Charge, му позволява да се втурне към враг и да удари по-силно след права тичане.",
    },
    "opt-companion-sea": {
        "en": "Summary (not the full stat block): a Medium beast of the water, with a Swim Speed of 60 feet. Its "
              "signature trait, Amphibious, lets it breathe both air and water.",
        "bg": "Резюме (не пълният блок с характеристики): звяр със среден размер на водата, със скорост "
              "на плуване 60 фута (18 м). Особеното му умение, Amphibious, му позволява да диша и "
              "въздух, и вода.",
    },
    "opt-companion-sky": {
        "en": "Summary (not the full stat block): a Small beast of the air, with a Fly Speed of 60 feet. Its "
              "signature trait, Flyby, keeps it from provoking Opportunity Attacks when it flies out of an "
              "enemy's reach.",
        "bg": "Резюме (не пълният блок с характеристики): малък звяр на въздуха, със скорост на летене "
              "60 фута (18 м). Особеното му умение, Flyby, не му позволява да предизвиква "
              "възможни атаки, когато излиза от обсега на враг.",
    },
}
for _t, _bg in _DTYPES.items():
    MESSAGES[f"opt-dtype-{_t}"] = {"en": _t, "bg": _bg}
