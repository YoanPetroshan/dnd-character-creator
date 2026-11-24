# Character sheet: D&D Beyond layout spec (measured 2026-11-24)

Measured on the owner's own D&D Beyond character sheet (Paladin 6), Chrome at 1470x714 (desktop) and 400 px wide (phone).
Values come from computed styles. We recreate the layout, sizes, type and behaviour. We do **not** copy their images, icons,
SVG frames, fonts files or code: frames are our own drawings in the same shapes, the font is Roboto / Roboto Condensed
(Google Fonts, Apache 2.0), and the theme colour is ours (D&D Beyond lets every character pick a theme colour; theirs was
red #c53131, ours is the Moss green).

## Typography (all sizes in px)

| Role | Font | Size | Weight | Colour | Case |
|---|---|---|---|---|---|
| Box label (STRENGTH, WALKING, CURRENT, ARMOR) | Roboto Condensed | 10 | 700 | #75838b | upper |
| Box title (PROFICIENCY / BONUS, SPEED, INITIATIVE, HIT POINTS, DEFENSES) | Roboto Condensed | 12-13 | 700 | #000 | upper |
| Big number (ability mod, prof, speed, HP, initiative, AC) | Roboto | 26 | 400-500 | #12181c | |
| Sign in front of a number (+ / -) | Roboto | 20 (12 in small rows) | 400 | #12181c at 60% | |
| Ability score under the box | Roboto | 16 | 700 | #000 | |
| Unit after a number (ft.) | Roboto | 16 | 500 | 60% | |
| Save / skill row label (STR, DEX) | Roboto Condensed | 12 | 700 | #000 (save) / #75838b (skill stat) | upper |
| Skill name | Roboto Condensed | 14 | 400 | #000 | |
| Skill bonus | Roboto 20 (sign 12) | | 400 | #12181c | |
| Table header (PROF MOD SKILL BONUS; ATTACK RANGE HIT/DC DAMAGE NOTES) | Roboto Condensed | 10-11 | 700 | #75838b / #000 | upper |
| Section footer title (SAVING THROWS, SENSES, SKILLS) | Roboto Condensed | 13 | 700 | #000 | upper, centred, at the BOTTOM of the box |
| Passive number | Roboto | 14 | 700 | #12181c | |
| Passive label | Roboto Condensed | 10 | 700 | #12181c | upper |
| Proficiency group label (ARMOR, WEAPONS, TOOLS, LANGUAGES) | Roboto Condensed | 14 | 700 | #75838b | upper |
| Proficiency items | Roboto Condensed | 13 | 400 | #000 | comma-separated |
| Primary tabs (ACTIONS SPELLS INVENTORY FEATURES & TRAITS BACKGROUND NOTES EXTRAS) | Roboto Condensed | 14 | 700 | active #12181c, others #75838b | upper; active has a 3px theme-colour underline |
| Filter pills (ALL ATTACK ACTION BONUS ACTION REACTION OTHER LIMITED USE) | Roboto Condensed | 12 | 700 | #75838b on light grey; active white on theme colour | upper |
| Section heading in a tab (ACTIONS • Attacks per Action: 2) | Roboto Condensed | 13 | 700 | theme colour | upper |
| Attack name / sub line | Roboto Condensed 14 #242528 / 10 #75838b | | | | |

## Desktop grid (sheet is 1200 px wide, centred)

```
y=0    header 100 tall: portrait 60x60 + name (Roboto Condensed ~22px 700) + "Species Class Level" small lines; right: rest buttons
y=92   quick-info row, 95 tall:
       6 ability boxes 81 wide, ~97 px apart (x 0,97,193,290,386,483)
       PROFICIENCY BONUS box 94x89 (x 579) | WALKING SPEED box 94x89 (x 688) | HEROIC INSPIRATION (x 796, 70 wide)
       HIT POINTS box (x ~880 to 1200): HEAL / [input] / DAMAGE column 70 wide, then CURRENT / MAX / TEMP
y=197  three columns, 10 px gutters:
       col 1 x 0, 281 wide:   SAVING THROWS box 200 tall | SENSES box 200 tall | PROFICIENCIES & TRAINING box 338 tall
       col 2 x 286, 281 wide: SKILLS box 765 tall (18 rows, ~36 px each)
       col 3 x 577, 623 wide: combat strip 95 tall (INITIATIVE hexagon 90 wide, ARMOR CLASS shield 90 wide,
                              DEFENSES | CONDITIONS box 408 wide, two halves split by a thin rule)
                              then the tab box 660 tall
```

## Boxes (shapes, our own drawings)

- White fill, theme-colour frame about 2 px, decorative corners.
- Ability box: tall frame with notched top corners; label at top; the modifier inside an inner rounded rectangle
  (1 px light grey #c3cbd0 border, radius ~4); the score in an oval that overlaps the bottom edge.
- Proficiency and Speed: rounded square frames; title on top, number middle, word at the bottom.
- Heroic Inspiration: small frame with an empty box, the label under it, outside the frame.
- Hit points: wide rounded frame; left column of three stacked small boxes (Heal green #40d250 text, an input, Damage red);
  CURRENT / MAX / TEMP labels on top, the big numbers under, a grey "/" between current and max; HIT POINTS title below.
- Initiative: hexagon (pointed left and right), label above outside it, value in an inner rounded rectangle.
- Armor Class: shield shape, ARMOR above the number, CLASS below.
- Saving throws: two columns of three pills; each pill = a dotted empty circle (or a filled dot when proficient) on the
  left, the ability abbreviation underlined with dots, and the value in a small rounded box on the right. Note line
  ("2 on saves") under them. Title SAVING THROWS at the bottom with a gear.
- Senses: three rows; the number in a rounded box on the left, a long pill with the label to its right. "Darkvision 60 ft."
  centred below. Title SENSES at the bottom.
- Proficiencies & Training: groups separated by thin rules, label grey upper case, items comma-separated.
- Skills: header row PROF MOD SKILL BONUS; each row: dotted circle / filled dot, stat (grey upper), skill name, bonus in a
  rounded box 40 wide on the right; thin rules between rows. Title SKILLS at the bottom.

## Tab box (desktop, col 3)

- Tab row of upper-case words; active = dark text + 3 px theme underline.
- Under it, filter pills for the tab (Actions: ALL ATTACK ACTION BONUS ACTION REACTION OTHER LIMITED USE).
- Content: section heading in theme colour ("ACTIONS • Attacks per Action: 2"), attack table with columns
  ATTACK (icon + name + sub line) | RANGE (number bold, long range grey in brackets, unit small) | HIT / DC (value in a rounded box) |
  DAMAGE (dice in a rounded box with a damage-type icon) | NOTES (grey).
- Then "Actions in Combat" as a comma list, then the action features as paragraphs with use boxes.

## Behaviour

- Clicking an attack, skill, save, spell, item or feature opens a **side panel 340 px wide on the right**, over the sheet,
  with the full details; the sheet stays where it is.
- Phone (<= ~760 px): a sticky top bar with portrait, name, "Species Class / Level", and a compact HIT POINTS box (current/max)
  with HEROIC INSPIRATION under it. Under it a strip: PROFICIENCY BONUS | WALKING SPEED | INITIATIVE | ARMOR CLASS | DEFENSES and
  CONDITIONS buttons. Then ONE section at a time; a round button bottom-right opens a menu of the sections:
  Abilities, Saves, Senses | Skills | Actions | Inventory | Spells | Features & Traits | Proficiencies & Training | Background |
  Notes | Extras. Abilities are a 3x2 grid of the same ability boxes; saves and senses follow on the same section.
  Passive senses on the phone are three round number boxes in a row with labels under.
