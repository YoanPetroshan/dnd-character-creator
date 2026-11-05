# Real-device checklist (iPhone Safari, Android Chrome)

Written 2026-10-23 at the close of the remaining program (RP22). Nothing here could be checked in the desktop browser pane; the user postponed it. Every item below was already checked at an emulated 375 px width (`document.documentElement.scrollWidth === 375` on ClassPage, BackgroundPage, EquipmentPage, ExportPage, no console errors, export buttons enabled). A real device adds what emulation cannot: native pickers, touch targets, storage lifetime, the download / share sheet, PDF fonts and network latency. Test at 360 and 375 px wide.

## Setup

1. On the dev machine run both servers on the LAN: `cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/flask --app server/app.py run --host 0.0.0.0 --port 8000` and `npm --prefix frontend run dev:lan` (script `dev:lan` = `vite --host`; the Vite proxy forwards `/api` to 127.0.0.1:8000). Open `http://<machine-LAN-IP>:5173/home` on the phone.
2. Put a draft on the phone. Easiest: write the JSON files on the dev machine and send them to the phone (AirDrop, Files), then open Home and use the "Качи чернова (.json)" button (the same file the "Изтегли чернова (.json)" button downloads). The files come from the kitchen-sink drafts (all picks made):

```
cd /Users/yoanpetrov/dnd-character-creator/server && ../.venv/bin/python - <<'EOF'
import sys, json; sys.path[:0] = ["tests", "."]
from catalog.loader import load
from engine.resolve import resolve
import kitchen_sink as ks
c = load()
ks.KITCHEN_SINK["bard10-2024"] = ks._sub("bard", 10, "2024", marks=(), origin=ks._XPHB_ORIGIN)
for sid in ["warlock7-2024", "evoker5-2024", "bard10-2014", "bard10-2024", "cleric7-2024", "fighter4-2024",
            "land-druid10-2024", "feats-mixed-wizard8", "warlock7-goo-2024", "wizard20-2024"]:
    d = ks.build(sid, c, resolve); d["draftVersion"] = 2
    json.dump(d, open(f"/tmp/{sid}.json", "w"), ensure_ascii=False)
EOF
```

(`/tmp` here is only the hand-off place for the phone; the files are not part of the repo.)

## Items

| # | What | Draft to import | URL / where | Pass when |
|---|---|---|---|---|
| 1 | Native `<select>` / ChoicePicker with long lists: Magical Secrets (381 options mixed / 2014, 339 under 2024) | `bard10-2014`, `bard10-2024` | `/class`, tab "Заклинания", card "Spells Known" | The list opens, scrolls, the search box filters (type "fire"), a pick can be added and removed, no horizontal scroll |
| 2 | Savant school lists | `evoker5-2024` | `/class`, tab "Заклинания", card "Evocation Savant" | Options readable, 3 picks possible, picks reach the spellbook |
| 3 | The ASI feat picker with 131+ options | any class at level 4 (e.g. `fighter4-2024`) | `/class`, tab "Способности", card "Ability Score Improvement" | The picker opens, feats with an unmet prerequisite show as disabled with the reason |
| 4 | The XPHB invocation list for Eldritch Adept (28 options) | start `feats-mixed-wizard8`, switch ruleset to 2024 on Home and take Eldritch Adept at an ASI level | `/class` | Prerequisite-gated options disabled with a reason, picks persist |
| 5 | Checkboxes and touch targets in "Носено и държано" and the nested equipment cards (holy symbol, same-as-above tool, pack contents line) | `cleric7-2024`, `fighter4-2024` | `/equipment` | Every checkbox / select can be hit with a thumb without mis-tapping a neighbour; nested cards readable |
| 6 | `localStorage` draft persistence across a tab kill and reload | any | kill the browser tab (swipe it away), reopen `/export` | The draft is still there (keys `dnd-builder-library-v1` and `dnd-builder-draft-v2:<id>` per character; an older single-draft `dnd-builder-draft-v2` is migrated on first load); in a private tab the page still works in memory |
| 7 | PDF download and open (Content-Disposition, iOS share sheet) and the Cyrillic DejaVu font in the device viewer | `warlock7-2024`, `land-druid10-2024` | `/export`, "Изтегли PDF" | On touch devices the share sheet opens (the page prefers `navigator.share`), the PDF opens, Bulgarian headings and `×` / curly quotes render, no "?" boxes |
| 8 | Markdown and YAML download on iOS | `wizard20-2024` | `/export`, "Изтегли Markdown" and "Изтегли YAML" | File saved or shared, opens as text, Bulgarian text intact |
| 9 | Sticky StepNav overflow | any | any page | The seven tabs scroll or fit, the active tab stays reachable, no horizontal page scroll |
| 10 | Long resource lists readable without horizontal scroll (RP10 / RP11) | `land-druid10-2024`, `warlock7-goo-2024`, `fighter4-2024` | `/class` (class resources) and `/export` (Ресурси на класа) | Long resource text wraps |
| 11 | Spells-tab routing of the new cards (Savant, Circle of the Land, Fey Wanderer Spells, Improved Illusions, Magical Discoveries, Lessons of the First Ones) | `evoker5-2024`, `land-druid10-2024`, `warlock7-2024` | `/class` tabs "Способности" and "Заклинания" | Each card sits on the tab named in its slice (spell-pick cards on "Заклинания", the rest on "Способности"); no card appears twice |
| 12 | `/api/resolve` latency on a mobile network for the heaviest drafts | a Bard 20 and a Warlock 20 with 10 invocations (raise a draft's level on Home / ClassPage) | any page after an edit | The page reacts within about a second on 4G; the server itself needs under 6 ms per resolve (measured RP22), so the rest is network and payload size |
| 13 | Optional / unavailable cards never block export | `wizard20-2024` with a spellbook that has no level 3 spell (Signature Spells shows as unavailable); `fey-wanderer3-2024` (Feywild Gifts is optional) | `/export` | "Всичко е готово за експорт" and the three download buttons enabled |
| 14 | Character library (SK4): several characters survive reload and a tab kill | `warlock7-2024` and `fighter4-2024` | `/home` | Import both drafts with "Качи герой или пакет (.json)" (two list rows, the old character is not replaced); open the second, edit its name, kill the browser tab, reopen `/home`: both characters and the edit are still there and the active one is the one you left; duplicate and delete work with the native confirm; "Изтегли всички (.json)" opens the share sheet and the file imports back (private tab: the list works in memory, the "не може да се запази" banner shows) |
| 15 | XL: English and Bulgarian PDF through the share sheet | `warlock7-2024` | `/home` language switch, then `/export`, "Изтегли PDF" / "Download PDF" once in each language | BG: the share sheet opens, headings are Bulgarian ("Бойни показатели", "Спасителни хвърляния"), `Spell Slots` stays English. EN: the share sheet opens, headings read "Combat Statistics", "Saving Throws", "Spell Slots: level 1: ...", no Cyrillic anywhere in the PDF (name typed in Latin), DejaVu renders `×` and curly quotes in both. A nameless hero shares as `герой.pdf` in BG and `character.pdf` in EN, titled "Безименен герой" / "Unnamed Character" |
| 16 | C1: the language switch survives a reload (and later a PWA restart) | any | `/home`, BG / EN buttons in the header | Switch to EN, reload the page: still EN (`<html lang="en">`, English titles on every route, the BG / EN control shows EN pressed). Kill the browser tab and reopen: still EN. Switch back to BG and repeat. In a private tab the switch still works for the visit and falls back to BG after a restart (storage blocked). When the offline program (O0-O5) ships: add the page to the home screen, switch to EN, force-quit the installed app and reopen it: still EN, with the network off as well |
| 17 | C1: screen readers read each language with the right voice | `warlock7-2024` | `/home` then `/sheet` in BG and in EN; VoiceOver (iOS) and TalkBack (Android) on | In BG the Bulgarian voice reads the headings and labels ("Клас броня (Armor Class, AC)", "Спасителни хвърляния (Saving Throws)"; since T1 the English term in brackets is read too: note whether the Bulgarian voice spells it out or reads it as English); in EN the English voice reads "Armor Class", "Saving Throws" (the voice follows `<html lang>`). Game names that stay English in BG (spell, feat and item names) are read in the Bulgarian voice or spelled out: note which, it is expected. Both buttons of the switch are announced with their pressed state and `lang`; no button is read as "button button" |
| 18 | C1: the random-name dice button works with the keyboard open at 375 px | any, empty name | `/home` at 375 px, iOS Safari and Android Chrome | Tap the Name field so the on-screen keyboard opens: the dice button next to the label is still fully visible and tappable (44 px) without scrolling or the keyboard covering it; one tap replaces the name with a new one (BG: Cyrillic first name + surname, same gender); the field keeps focus or the keyboard closes without a layout jump; repeated taps give different names; no horizontal scroll; the draft saves the new name |
| 19 | C1: names in English are transliterated | none | `/home`, language EN, dice button | The name is Latin only (for example "Bogdana Draganova", "Shishman Goranov"), never Cyrillic, never "?" boxes; the same name typed into the PDF export shares as a PDF with the Latin name. Switch to BG and tap again: a Cyrillic name |
| 20 | T1: the English term in brackets fits the narrow screens | `warlock7-2024`, `wizard20-2024` | `/sheet`, `/class`, `/background`, `/species`, `/abilities`, `/export` in BG at 375 px, then the printed sheet (`/sheet` print preview) | The step bar (`Произход (Background)`, `Раса (Species)`) scrolls or wraps without a horizontal page scroll; the table column heads `Характеристика (Ability)`, `Владеене (Proficiency)` and the marker `експертиза (Expertise)` wrap inside their cells and stay readable; the long labels (`DC на спасяването от заклинание (Spell Save DC)`, `Бонус за атака със заклинание (Spell Attack Modifier)`, `Зарове за точки живот (Hit Point Dice)`) wrap on their own lines; resource lines (`Rage: 3, дълга почивка (Long Rest), щета +2`) wrap; the BG PDF (`/export`, "Изтегли PDF") shows the long caster line (save DC and attack modifier) on two lines without clipping |

## Report back

For each failing row: device, browser, width, what happened, a screenshot. Functional problems (a picker that cannot be used, a download that fails, a lost draft) are bugs; visual polish belongs to the separate visual design pass (open question 12).
