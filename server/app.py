"""Phase 0 stub backend for the v2 character builder.

Serves exactly one real endpoint, /api/resolve, which currently returns a
hardcoded Resolution regardless of the request body — no rules engine
exists yet. Phase 1 replaces the hardcoded body with a real
resolve(draft, catalog) call; the route and the response shape stay
exactly the same, which is the whole point of nailing the shape now.

This file imports nothing from v1 (chargen/, app.py at the repo root,
etc.) — v2 is a from-scratch rewrite of everything except the bundled SRD
JSON data, and that data isn't even read yet in Phase 0.
"""
from __future__ import annotations

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})


def _stub_resolution() -> dict:
    """A hand-written Resolution covering every Choice shape Phase 0's
    frontend needs to prove out: a pending single-choice (Fighting Style),
    a resolved multi-choice (skill proficiencies, already picked), a
    pending multi-choice from a different source kind (background
    languages), and a choice with one disabled option carrying a reason
    (Draconic Ancestry — Gold disabled, simulating a 2024-only option not
    available from the currently enabled sources).
    """
    return {
        "sheet": {"name": "", "level": 0},
        "choices": [
            {
                "id": "class:fighter:1:fighting-style",
                "source": {"kind": "class", "id": "fighter", "label": "Fighter", "level": 1},
                "label": "Fighting Style",
                "description": "You adopt a particular style of fighting as your specialty.",
                "count": 1,
                "options": [
                    {"id": "archery", "label": "Archery"},
                    {"id": "defense", "label": "Defense"},
                    {"id": "dueling", "label": "Dueling"},
                    {"id": "great-weapon-fighting", "label": "Great Weapon Fighting"},
                ],
                "selected": [],
                "status": "pending",
            },
            {
                "id": "class:fighter:1:prof-skills",
                "source": {"kind": "class", "id": "fighter", "label": "Fighter", "level": 1},
                "label": "Skill Proficiencies",
                "description": "Choose two skills from the Fighter list.",
                "count": 2,
                "options": [
                    {"id": "acrobatics", "label": "Acrobatics"},
                    {"id": "athletics", "label": "Athletics"},
                    {"id": "intimidation", "label": "Intimidation"},
                    {"id": "perception", "label": "Perception"},
                ],
                "selected": ["athletics", "perception"],
                "status": "resolved",
            },
            {
                "id": "background:acolyte:languages",
                "source": {"kind": "background", "id": "acolyte", "label": "Acolyte"},
                "label": "Languages",
                "description": "Choose two languages of your choice.",
                "count": 2,
                "options": [
                    {"id": "celestial", "label": "Celestial"},
                    {"id": "draconic", "label": "Draconic"},
                    {"id": "dwarvish", "label": "Dwarvish"},
                ],
                "selected": [],
                "status": "pending",
            },
            {
                "id": "species:dragonborn:ancestry",
                "source": {"kind": "species", "id": "dragonborn", "label": "Dragonborn"},
                "label": "Draconic Ancestry",
                "description": "Choose the type of dragon you're descended from.",
                "count": 1,
                "options": [
                    {"id": "black", "label": "Black (Acid)"},
                    {"id": "blue", "label": "Blue (Lightning)"},
                    {
                        "id": "gold",
                        "label": "Gold (Fire)",
                        "disabled": True,
                        "disabledReason": "requires the 2024 species pack",
                    },
                ],
                "selected": [],
                "status": "pending",
            },
        ],
        "derived": {"ac": 10, "hp": 0, "profBonus": 2},
        "problems": [],
        "warnings": [
            {"id": "stub-warning", "message": "This is Phase 0 stub data — no rules engine runs yet."}
        ],
        "pruned": [],
    }


@app.route("/api/health")
def health():
    return jsonify({"ok": True})


@app.route("/api/resolve", methods=["POST"])
def resolve():
    _draft = request.get_json(silent=True) or {}  # ignored in Phase 0
    return jsonify(_stub_resolution())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
