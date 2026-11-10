"""The fixed request list shared by the O0 baseline (test_service_baseline.py) and the service/Flask equality test
(test_service.py). Each entry: (name, method, url, body bytes or None, content type or None). The urls carry the
query string; paths are percent-encoded as a client would send them."""
from __future__ import annotations

import json

JSON = "application/json"


def fighter_draft() -> dict:
    return {
        "name": "Torvin Bracewell",
        "sources": ["srd"],
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
        "equipment": {"added": [], "skipped": False},
        "details": {},
    }


def exportable_draft(name: str | None = "Torvin Bracewell") -> dict:
    draft = fighter_draft()
    draft["classes"][0]["choices"] = {
        "class:fighter:1:prof-choice-0": ["skill-acrobatics", "skill-athletics"],
        "class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-archery"],
    }
    draft["equipment"]["choices"] = {
        "class:fighter:1:equipment-choice-0": ["chain-mail"],
        "class:fighter:1:equipment-choice-2": ["handaxe"],
        "class:fighter:1:equipment-choice-3": ["explorers-pack"],
    }
    draft["background"]["choices"] = {"background:acolyte:languages": ["dwarvish", "elvish"]}
    draft["species"]["choices"] = {"species:human:languages": ["giant"]}
    if name is None:
        draft.pop("name")
    else:
        draft["name"] = name
    return draft


def _j(value) -> bytes:
    return json.dumps(value).encode("utf-8")


def _build() -> list[tuple]:
    reqs: list[tuple] = []

    def add(name, method, url, body=None, ctype=None):
        reqs.append((name, method, url, body, ctype))

    def post(name, url, value, ctype=JSON):
        add(name, "POST", url, _j(value), ctype)

    # health
    add("health", "GET", "/api/health")
    add("health-query-ignored", "GET", "/api/health?lang=fr&x=1")
    # resolve
    post("resolve-empty", "/api/resolve", {})
    post("resolve-fighter", "/api/resolve", fighter_draft())
    post("resolve-exportable", "/api/resolve", exportable_draft())
    post("resolve-lang-bg", "/api/resolve?lang=bg", fighter_draft())
    post("resolve-lang-en", "/api/resolve?lang=en", fighter_draft())
    post("resolve-lang-bg-empty-draft", "/api/resolve?lang=bg", {})
    for bad in ("fr", "", "BG", "bg,en", "en%20"):
        post(f"resolve-bad-lang-{bad or 'empty'}", f"/api/resolve?lang={bad}", {})
    post("resolve-lang-twice-first-wins", "/api/resolve?lang=bg&lang=fr", fighter_draft())
    post("resolve-bad-lang-and-list-body", "/api/resolve?lang=xx", [1])
    for label, value in (("list", [1, 2]), ("string", "x"), ("number", 3), ("bool", True)):
        post(f"resolve-body-{label}", "/api/resolve", value)
    post("resolve-body-null", "/api/resolve", None)
    add("resolve-no-body", "POST", "/api/resolve")
    add("resolve-empty-body-json-ct", "POST", "/api/resolve", b"", JSON)
    add("resolve-invalid-json", "POST", "/api/resolve", b"{not json", JSON)
    add("resolve-invalid-utf8", "POST", "/api/resolve", b"\xff\xfe\x00{", JSON)
    add("resolve-text-ct-ignores-body", "POST", "/api/resolve", _j([1]), "text/plain")
    add("resolve-vendor-json-ct", "POST", "/api/resolve", _j(fighter_draft()), "application/vnd.x+json")
    add("resolve-json-charset-ct", "POST", "/api/resolve", _j(fighter_draft()), "application/json; charset=utf-8")
    post("resolve-nonascii-name", "/api/resolve", {**fighter_draft(), "name": "Ана — \U0001F409"})
    post("resolve-junk-ids", "/api/resolve", {"classes": [{"classId": "nope", "level": 3}], "species": {"id": "x"}})
    # catalog
    add("catalog", "GET", "/api/catalog")
    add("catalog-2024", "GET", "/api/catalog?ruleset=2024")
    add("catalog-2014", "GET", "/api/catalog?ruleset=2014")
    add("catalog-2024-srd-fallback", "GET", "/api/catalog?ruleset=2024&sources=srd")
    add("catalog-sources", "GET", "/api/catalog?sources=phb,xge,,tce")
    add("catalog-junk-ruleset", "GET", "/api/catalog?ruleset=zzz")
    add("class-fighter", "GET", "/api/catalog/class/fighter")
    add("class-fighter-2024", "GET", "/api/catalog/class/fighter?ruleset=2024")
    add("class-fighter-include", "GET", "/api/catalog/class/fighter?include=champion&sources=srd")
    add("class-wizard-2014-phb", "GET", "/api/catalog/class/wizard?ruleset=2014&sources=phb")
    add("class-cleric", "GET", "/api/catalog/class/cleric")
    add("class-unknown", "GET", "/api/catalog/class/nope")
    add("class-unknown-nonascii", "GET", "/api/catalog/class/%D0%BA")
    add("class-empty-id", "GET", "/api/catalog/class/")
    add("class-with-slash", "GET", "/api/catalog/class/a%2Fb")
    add("background-acolyte", "GET", "/api/catalog/background/acolyte")
    add("background-unknown", "GET", "/api/catalog/background/nope")
    add("species-human", "GET", "/api/catalog/species/human")
    add("species-elf", "GET", "/api/catalog/species/elf")
    add("species-unknown", "GET", "/api/catalog/species/nope")
    # items
    add("items", "GET", "/api/items")
    add("items-category-q", "GET", "/api/items?category=weapon&q=SWORD")
    add("items-2024-sources", "GET", "/api/items?ruleset=2024&sources=phb&q=rope")
    add("items-no-match", "GET", "/api/items?q=zzzzzz")
    # spells
    add("spells-all", "GET", "/api/spells")
    add("spells-wizard", "GET", "/api/spells?class=wizard")
    add("spells-wizard-level-q", "GET", "/api/spells?class=wizard&level=1&q=FIRE")
    add("spells-cantrips", "GET", "/api/spells?class=cleric&level=0&ruleset=2024&sources=phb")
    add("spells-unknown-class", "GET", "/api/spells?class=nope")
    add("spells-level-empty", "GET", "/api/spells?class=wizard&level=")
    add("spells-level-bad", "GET", "/api/spells?class=wizard&level=x")
    add("spells-level-float", "GET", "/api/spells?class=wizard&level=1.5")
    add("spells-level-spaces", "GET", "/api/spells?class=wizard&level=%202%20")
    add("spells-level-negative", "GET", "/api/spells?class=wizard&level=-1")
    add("spell-fireball", "GET", "/api/spells/fireball")
    add("spell-alias-or-unknown", "GET", "/api/spells/Fireball")
    add("spell-unknown", "GET", "/api/spells/no-such-spell")
    add("spell-cantrip", "GET", "/api/spells/fire-bolt")
    # exports
    full = exportable_draft()
    for fmt in ("yaml", "markdown", "pdf"):
        post(f"export-{fmt}", f"/api/export/{fmt}", full)
        post(f"export-{fmt}-lang-bg", f"/api/export/{fmt}?lang=bg", full)
        post(f"export-{fmt}-lang-en", f"/api/export/{fmt}?lang=en", full)
        post(f"export-{fmt}-bad-lang", f"/api/export/{fmt}?lang=fr", full)
        post(f"export-{fmt}-gate-empty", f"/api/export/{fmt}", {})
        post(f"export-{fmt}-gate-bg", f"/api/export/{fmt}?lang=bg", fighter_draft())
        post(f"export-{fmt}-gate-en", f"/api/export/{fmt}?lang=en", fighter_draft())
        post(f"export-{fmt}-nameless", f"/api/export/{fmt}", exportable_draft(None))
        post(f"export-{fmt}-nameless-bg", f"/api/export/{fmt}?lang=bg", exportable_draft(None))
        post(f"export-{fmt}-nameless-en", f"/api/export/{fmt}?lang=en", exportable_draft(None))
        post(f"export-{fmt}-name-empty-string", f"/api/export/{fmt}?lang=bg", exportable_draft(""))
        post(f"export-{fmt}-name-special", f"/api/export/{fmt}", exportable_draft('A/B\\C:D*E?"F<G>H|I'))
        post(f"export-{fmt}-name-cyrillic", f"/api/export/{fmt}", exportable_draft("Ана/Борис"))
        post(f"export-{fmt}-name-number", f"/api/export/{fmt}", {**full, "name": 123})
        post(f"export-{fmt}-body-list", f"/api/export/{fmt}", [1])
        add(f"export-{fmt}-no-body", "POST", f"/api/export/{fmt}")
        add(f"export-{fmt}-invalid-json", "POST", f"/api/export/{fmt}", b"{x", JSON)
    post("export-docx-404", "/api/export/docx", full)
    post("export-docx-bad-lang-still-404", "/api/export/docx?lang=fr", full)
    post("export-bad-lang-before-body", "/api/export/yaml?lang=zz", [1])
    post("export-name-unicode-md-bg", "/api/export/markdown?lang=bg", exportable_draft("Жé \U0001F409"))
    # unknown paths and wrong methods
    add("api-unknown", "GET", "/api/nope")
    add("api-root", "GET", "/api")
    add("api-root-slash", "GET", "/api/")
    add("api-trailing-slash", "GET", "/api/health/")
    add("api-catalog-unknown-kind", "GET", "/api/catalog/weapon/x")
    add("api-deep-unknown", "GET", "/api/a/b/c")
    add("api-post-unknown", "POST", "/api/nope", _j({}), JSON)
    add("api-delete-unknown", "DELETE", "/api/nope")
    add("api-get-resolve", "GET", "/api/resolve")
    add("api-get-export", "GET", "/api/export/yaml")
    add("api-post-health", "POST", "/api/health", _j({}), JSON)
    add("api-put-catalog", "PUT", "/api/catalog", _j({}), JSON)
    add("api-delete-items", "DELETE", "/api/items")
    add("api-post-spells", "POST", "/api/spells", _j({}), JSON)
    add("api-post-class", "POST", "/api/catalog/class/fighter", _j({}), JSON)
    add("api-patch-spell", "PATCH", "/api/spells/fireball")
    # VF7.6: a lone-surrogate name, a very long name, a body nested too deeply, a body over the 1 MB limit
    for fmt in ("yaml", "markdown", "pdf"):
        post(f"export-{fmt}-name-lone-surrogate", f"/api/export/{fmt}", exportable_draft("\ud800"))
        post(f"export-{fmt}-name-5000-chars", f"/api/export/{fmt}", exportable_draft("N" * 5000))
    add("resolve-body-nested-450k", "POST", "/api/resolve", b"[" * 450000, JSON)
    add("export-yaml-body-nested-70", "POST", "/api/export/yaml", b'{"name":' + b"[" * 70 + b"]" * 70 + b"}", JSON)
    add("resolve-body-over-1mb", "POST", "/api/resolve", b'{"name":"' + b"x" * 1_000_001 + b'"}', JSON)
    return reqs


REQUESTS: list[tuple] = _build()
