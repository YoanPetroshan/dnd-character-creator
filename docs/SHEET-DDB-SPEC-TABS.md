# Character sheet: D&D Beyond tabs, side panel, header, phone, theme (measured 2026-11-24)

Second pass. The first pass is `SHEET-DDB-SPEC.md` (top row, three left columns, Actions tab). Same rules: we rebuild shapes, sizes,
type and behaviour; we do not copy images, icons or code. Font names: RC = Roboto Condensed, R = Roboto.
Measured on the owner's own Paladin 6 sheet. Desktop window: innerWidth 1470, innerHeight 770 (not 857, see "Not measured").
All x / y are relative to the `.ct-character-sheet-desktop` box (the 1200 px sheet), unless stated. Colours are computed values.

Shared colours: ink #12181c, black #000, grey label #75838b, grey row text #242528, table-head black #000, light grey chip #ecedee,
rule / box border light grey #d8d8d8, theme red #c53131, white page card.

---------------------------------------------------------------------------------------------------

## 1. The tab box (frame for all tabs)

| Thing | Value |
|---|---|
| Box | x 577, y 301, 623 wide, 660 tall (same on every tab) |
| Inner content width | 583 (x 597 to 1180, i.e. 20 px padding each side) |
| Tab row | y 314, 23 tall. Buttons are RC 14 / 700 / upper, padding 3 px 0, gap between words 16 px |
| Tab x / width | Actions 597/52, Spells 665/43, Inventory 724/67, Features & Traits 807/115, Background 938/80, Notes 1035/38, Extras 1089/46 |
| Active tab | text #12181c, border-bottom 3 px solid theme red |
| Inactive tab | text #75838b, border-bottom 3 px transparent. Hover: cursor pointer only, colour does not change |
| Scrolling | Only the content under the tab row scrolls (the element ends at the bottom of the box). Tab row, summary, search and filter pills stay fixed. A thin grey (about #c3cbd0) scrollbar thumb, 6 px wide, appears on the right edge |
| Content start | filter pills at y ~356 (Features / Background / Notes), ~451 (Spells), ~515 (Inventory). Scroll area starts right under the pills (y 493 on Spells, 511 on Inventory, 397 on Features) |

### Filter pills (same on every tab)
- Button, RC 12 / 700 / upper, height 23 (22 on Inventory/Features), padding 2 px 5 px, border 2 px solid same colour as fill, radius 4.
- Inactive: bg #ecedee, text #75838b. Active: bg theme red, text #f9fafa. Hover (inactive): bg #525c63, text #ecedee, cursor pointer.
- Gap between pills 4 px. First pill is always ALL.

### Section heading inside a tab
- RC 13 / 700 / upper, theme red, a 1 px light rule under it across 583 px, height 18. Gap from heading to first content about 9 px.
- Sub-heading (for example "Paladin Features"): RC 15 / 700, theme red, not upper, height 21.
- "Manage ..." link buttons (Manage Spells, Manage Inventory, Manage Feats, Manage Extras, Manage Custom): RC 10 / 400 / upper, theme red text, 1 px theme border, radius 3, padding 6 px 10 px, white bg, height 26.

---------------------------------------------------------------------------------------------------

## 2. ACTIONS tab (other pills; first pass has the ALL view)

Pills: ALL, ATTACK, ACTION, BONUS ACTION, REACTION, OTHER, LIMITED USE (x 597.., y 451 in the page, 23 tall).
Section heading row: "ACTIONS • Attacks per Action: 2" at left, MANAGE CUSTOM (theme red, RC 10 bold upper, no box) at right edge.

| Pill | What it shows |
|---|---|
| ALL | Attacks table, "Actions in Combat" comma list, then action features, then "Bonus Actions" block (spell/feature rows), reactions, other |
| ATTACK | only the attacks table (Javelin, Longsword, Shortbow, Spear, Unarmed Strike, Breath Weapon) |
| ACTION | "Actions in Combat" list plus action features with their use boxes (Breath Weapon (Fire), Channel Divinity, Sacred Weapon, Sap weapon masteries, Unarmed Strike) |
| BONUS ACTION | "Bonus Actions" heading, "Actions in Combat", Spells sub-block, bonus-action features (Divine Sense, Draconic Flight, Lay On Hands with a Current counter) |
| REACTION | "Reactions" heading plus "Actions in Combat" only |
| OTHER | "Other" heading plus "Actions in Combat" only |
| LIMITED USE | only things with use counters, grouped under Actions / Spells / Bonus Actions (Breath Weapon, Channel Divinity, Draconic Flight; each with a use box and "/ Long Rest") |

Attack table rows are about 46 px high; a second damage line (versatile) is a smaller grey rounded box under the first. Star icon in red on mastery weapons.

---------------------------------------------------------------------------------------------------

## 3. SPELLS tab

### Layout top to bottom
| Block | y | Content |
|---|---|---|
| Summary row (centred, 3 groups) | ~353 | `+2 MODIFIER` / `+5 SPELL ATTACK` / `13 SAVE DC`. Value RC 16 / 700 (#12181c; DC is #000); sign "+" RC 12 / 700 theme-coloured-less dark green-grey sign (rendered at 60 % ink). Label RC 10 / 700 / upper / #75838b under the value. Groups about 65 px apart, bottom rule 1 px light |
| Search row | ~405 | search box 412 wide x 34 tall (input 24 tall, magnifier icon left, placeholder "Search Spell Names, Casting Times, Damage Types, Conditions or Tags", 1 px grey border, radius 4); a filter funnel icon (dark) right of it; MANAGE SPELLS button (91 x 26) at the far right |
| Filter pills | y 451 | ALL, 1ST, 2ND (one pill per spell level the character has; no cantrip pill because there are none), plus one small pill with a diamond/concentration icon (concentration filter), 26 wide |
| Level group | y 496 | "1ST LEVEL" RC 13 / 700 / upper theme red at left, then at right "SLOTS" RC 13 / 700 black preceded by the slot boxes |

### Slots
- Slot boxes: 20 x 20, white, 1 px #d8d8d8, no radius, gap 4 px. Used slot = red filled square inside (about 12 px, theme red). 1st level shows 4 boxes (first one filled red = 1 used... the filled one is the SPENT one), 2nd level shows 2.
- Slot group is 96 / 135 px wide, right-aligned to the 583 px edge.

### Table
- Header row (RC 11 / 700 / upper / black, 25 tall): NAME x 632 (135 wide), TIME x 767 (35), RANGE x 802 (55), HIT / DC x 857 (45), EFFECT x 902 (85), NOTES x 987 (193). The first 35 px (x 597) is the cast-button column (no header).
- Row: padding 8 px 0, content min 42 tall (rows are 47-53 px pitch; two-line names are taller). Dotted or very light 1 px bottom rule between rows. No hover background (cursor pointer only).
- Cast cell (x 597, 30 x 22): button, bg theme red, white text RC 8 / upper "CAST", radius 3, padding 5. A spell that is a limited-use feature shows "USE" instead of CAST. A spell that can be cast at a level other than its own shows a small blue tag (bg about #1c9aef) "1ST" above a GREY CAST button (bg #ecedee-ish, grey text) when you are looking at the all-levels list (that is how upcasts of lower-level spells look under the 2ND LEVEL group).
- Name cell: spell name RC 14 / 400 italic / #12181c; source line under it RC 10 / 400 / #75838b ("Paladin", "Oath of Devotion Spells", "Paladin's Smite"). After the name a small black diamond-with-letter icon (concentration). Long names wrap onto two lines (width 135).
- Time: R 13 / 400 black ("1A" action, "1BA" bonus action, "1R" reaction).
- Range: number R 14 / 700 #12181c + unit "ft." R 10 / 700 at 60 % opacity; words (Self, Touch) R 12-13 / 400 black.
- Hit / DC: "--" R 13 / #75838b when none; a save shows the ability abbreviation over the DC number (e.g. "CHA" small above "13") in RC 10 / 700 and R 13.
- Effect: either plain word (Buff, Control, Summoning, "Buff*") RC 12 / 400 black, or a damage/heal box: 49 x 36, 1 px #d8d8d8 border, radius 4, value R 13 / #394b59 ("2d8") plus a damage-type icon right of it ("5 heart" for healing).
- Notes: RC 12 / 400 / #75838b, comma and slash separated components ("D: 1m, V/S/M"); a special note is shown in blue (#1c9aef, e.g. "Targets: +1"); area shows a range number plus a tiny sphere icon ("15 ft. sphere").
- Two "Divine Smite" rows: different sources (Paladin, Paladin's Smite) are separate rows.

### Empty state / other
- No spells in a level: the level group is simply not shown. With no spells at all a message and the manage button appear (not seen, character has spells).

---------------------------------------------------------------------------------------------------

## 4. INVENTORY tab

| Block | y | Content |
|---|---|---|
| Sub-tabs MY INVENTORY | PARTY INVENTORY | 353 | two halves, 292 wide each, 50 tall, RC-like R 14 / 500 upper. Active: theme red text and a 2-3 px theme underline across the half; inactive #75838b |
| Weight row | 410 | left: "WEIGHT CARRIED: **116** lb." (RC 13 / 700 upper ink; "lb." RC 10) with "UNENCUMBERED" under it (RC 10 / 700 / #75838b / upper). Right: currency row |
| Currency row | 413 | pairs "13 [gold coin icon]  5 [silver coin icon]", numbers RC 14 / 700 black, icons about 14 px, gap 10 px. Clickable (opens currency panel). Only non-zero coins shown |
| Rule | | 1 px light under the weight row |
| Search row | ~476 | same as Spells: search input, funnel, MANAGE INVENTORY button (right) |
| Filter pills | 515 | ALL, EQUIPMENT, BACKPACK, QUIVER, ATTUNEMENT, OTHER POSSESSIONS (x 597, 634, 710, 782, 837, 923) |

### Table
- Header (RC 11 / 700 / upper / black, 20 tall): ACTIVE x 597 (40), NAME x 637 (200), WEIGHT x 837 (50), QTY x 887 (35), COST (GP) x 922 (50), NOTES x 972 (208).
- Group header row: container name RC 13 / 700 / upper black ("EQUIPMENT"), count "(11)" RC 13 / #75838b, group weight "86 lb." R 13 / 700 at the WEIGHT column. For a container (Backpack, Quiver) the heading is #242528, a 20 x 20 box in front (red filled = the container itself is equipped) and the weight reads "29 lb. (24/30 lb)" (carried / capacity, capacity in grey).
- Item row: 41 tall (padding 8 px 0), 1 px dotted light bottom rule, no hover colour.
  - Active cell: a 20 x 20 box, white, 1 px #d8d8d8. Equipped = filled red square inside. Not equipped but equippable (Chain Mail) = empty box. Not equippable = a grey dash "--" (R 13 / #75838b).
  - Name R 13 / 400 / #242528; under it a type line RC 10 / 400 / #75838b "Gear - Holy Symbol", "Heavy Armor - Chain Mail", "Legacy - Gear - Tool".
  - Weight R 13 / 400 / #12181c + "lb." R 10; "--" when none.
  - Qty R 13 black; "--" when 1-of-a-kind without count.
  - Cost R 13 black (gp, no unit). 
  - Notes: RC 12 / 400 / #75838b, comma list of tags and key stats ("AC 16, Str 13, Stealth", "Simple, Thrown, Slow, Range (30/120)", "+2 AC"). A small red hexagon with a letter marks a legacy/rule-set badge after the notes.
- After every container's last row: left link "+ Add Equipment" / "+ Add items to your Backpack" (R 13 / black) and right link "Hide Contents" (R 13 / black, right aligned). Rows fold away with it.
- ATTUNEMENT section (RC 13 theme red heading, rule): left column "ATTUNED ITEMS" (RC 10 / 700 / #75838b) with three empty slot pills (pill 150 x 50, light grey outline #d8d8d8, round left end, text "Choose an Item from the Right" R 13 / #75838b); right column "ITEMS REQUIRING ATTUNEMENT" and "PARTY ITEMS REQUIRING ATTUNEMENT" with centred grey empty-state sentences (R 13 / #75838b).
- OTHER POSSESSIONS section: heading in theme red, rule, then empty state link "+ Add other possessions, treasure, or holdings for your character in this section." (R 13 / #75838b).
- Order in the scroll area: Equipment, Backpack, Quiver, Attunement, Other Possessions.

---------------------------------------------------------------------------------------------------

## 5. FEATURES & TRAITS tab

- Pills: ALL, CLASS FEATURES, SPECIES TRAITS, FEATS (x 597, 634, 738, 836; y 356, 22 tall).
- Groups in order, each starting with a theme-red RC 13 / 700 / upper heading with rule: **CLASS FEATURES**, **SPECIES TRAITS**, **FEATS**. Inside CLASS FEATURES a sub-heading by class ("Paladin Features", RC 15 / 700 theme red); features of a subclass appear in the same list.
- Feature block: title RC 13 / 700 / black; then " • " grey dot; then source "PHB-2024" R 11 italic and ", pg. 109" R 11 regular (all black, 13 tall). Under feats / background items an extra line "FROM **Paladin**" (RC 10 / 700 / #75838b "From" + RC 11 / 700 black).
- Description: R 12 / 400 / black, line height about 17, paragraph gap about 4-6 px. **Text is shown in full: there is no Show more / collapse on this tab.**
- Choice or detail sub-block (selected skills, weapon masteries, ability scores): a 3 px solid #d8d8d8 left bar, padding-left 8 px (text at x 612 against 597), lines R 12 black; sub-titles inside it RC 12 / 700 ("Longsword (Sap)").
- Use counters inside a feature (Lay On Hands): lines "Uses: **30** / Long Rest" (R 12, number bold), "Current:" with a red 24 x 24 minus square button, the number R 12 / 700, a grey (disabled) plus square; and for per-rest features an empty 24 x 24 box (white, 1 px #d8d8d8) followed by "/ Long Rest". Action lines like "Lay On Hands: Heal: 1 Bonus Action" are plain R 12.
- Gap between feature blocks about 14-18 px. Feats group has a centred MANAGE FEATS button right under the heading (inside rules).
- Total scroll height with everything: 2827 px in a 435 px window.

---------------------------------------------------------------------------------------------------

## 6. BACKGROUND tab

- Pills: ALL, BACKGROUND, CHARACTERISTICS, APPEARANCE.
- BACKGROUND (heading theme red): background name "Soldier" RC 15 / 700 black (not red), then the granted feature block in the same style as Features (title RC 13 / 700, source line, "From Soldier", left-bar sub-block with the chosen scores; first line RC 12 / 700).
- CHARACTERISTICS: a grid of 5 equal columns (117 px each, 583 wide), two rows. Labels R 11.2 / 700 / upper / #12181c: ALIGNMENT, GENDER, EYES, SIZE, HEIGHT / FAITH, HAIR, SKIN, AGE, WEIGHT. Values R 13 / 400 under them, "--" when empty. 1 px rule under the grid.
- Then personality blocks, each: title RC 13 / 700 black ("Personality Traits", "Ideals", "Bonds", "Flaws"), text R 12 / 400 black under it. Empty = "+ Add Bonds" R 12 / #75838b.
- APPEARANCE heading, empty state "+ Add Appearance information" R 13 / #75838b.
- Scroll height about 606 + inner.

---------------------------------------------------------------------------------------------------

## 7. NOTES tab

- Pills: ALL, ORGS, ALLIES, ENEMIES, BACKSTORY, OTHER.
- Five sections each with a theme-red RC 13 / 700 upper heading and rule: ORGANIZATIONS, ALLIES, ENEMIES, BACKSTORY, OTHER. Section pitch about 46-47 px when empty.
- Empty: "+ Add Organizations" / "+ Add Allies" / "+ Add Enemies" / "+ Add Other" R 12 / 400 / #75838b, 17 tall, 9 px under the rule.
- Filled: free text R 12 / 400 black, line height about 17, paragraphs separated by line breaks (backstory 235 tall).

---------------------------------------------------------------------------------------------------

## 8. EXTRAS tab

- No pills. Search row at the top (same as Spells): search "Search Names, Types, or Tags", funnel, MANAGE EXTRAS button.
- Empty state: one centred line "Extras that you add will display here." R 13 / 400 / #75838b, vertically centred in the empty area (about 209 wide, 547 tall box).

---------------------------------------------------------------------------------------------------

## 9. Side panel (sidebar) on desktop

| Thing | Value |
|---|---|
| Position | right edge of the browser window (not of the sheet), x = viewport right - 340, **340 wide**, overlays the sheet; the sheet does not move or resize. Top edge sits on the sheet's top (about 124 px below the site header at scroll 0); height about 966 (runs past the viewport; it scrolls with the page, content area itself has overflow auto) |
| Strip above the panel | small dark strip with: a double-chevron (collapse, tooltip "Hide Sidebar"), a padlock (unlocked), and at the far right two layout icons (left-pane / right-pane) |
| Frame | white (#fefefe) body, 2 px theme-red outline, rounded top corners (about 12 px), with a small dark emblem notched into the top centre. Own drawing for us: red rounded rectangle plus a notch |
| Padding | 13 px left and right (content 314 wide), a 10 px gap at the top |
| Closing | the double-chevron in the strip collapses it; when collapsed only a small "<<" handle stays at the top right of the window. Opening another thing replaces the content (no stacking). Escape did not close it in our test; there is no X |
| Body type | R 13 / 400 / #12181c; labels bold R 13.008 / 700; units "ft." / "lb." R 10 |
| Section toggle | "Customize" R 13 / 700 with a grey chevron right, rule above and below (1 px light red-tinted #e3b4b4-ish for the first sheets, light grey otherwise). Collapsed by default |
| Description rule | 1 px light rule, then description R 13 / 400, line height ~18 |

### Content per kind
| Opened by | Header | Body |
|---|---|---|
| Attack / item (Javelin) | provenance none; 32 x 32 item thumbnail with 1 px border, title RC 18 / 700 #242528, a red pencil icon (edit) right of the title | italic type line ("Weapon, common"), "In Equipment", "Equipped" (R 13), Customize, key/value list (Proficient, Attack Type, Reach, Range, Damage, Damage Type with icon, Weight, Cost, Properties, Source in italics), rule, description paragraph, TAGS: chips (R 10 / 700 upper, 1 px border #d8d8d8, bg white, padding 4 x 8), rule, centred Quantity stepper (red 24 x 24 minus / white input 56 x 24 / red plus), then three small buttons UNEQUIP (solid red), MOVE (outline with chevron), DELETE (outline). **These write data: we never clicked them** |
| Spell (Divine Smite) | small provenance line "Paladin" R 13, then 32 x 32 red square tile with the white school icon, name RC 18 / 700 **italic**, pencil icon; italic line "1st Level Evocation" | CAST row: label "CAST" RC 13 / 700 + red button "SPELL SLOT" (RC 10 white, 78 x 26) with a tiny circled count badge "3" on its top-left corner (RC 10 / 700 theme red, white bg, red border); at the right "LEVEL" label, grey minus square, "1st", red plus square. Then "2d8 [icon] Damage" R 14 and a grey R 12 note in brackets. Customize. Then Casting Time, Range/Area, Components, Duration, Source rows (bold label, value; label wraps and value hangs). Rule. Description R 13. "Using a Higher-Level Spell Slot." bold-italic run-in head. TAGS chips |
| Feature (Lay On Hands) | provenance "Paladin", 32 x 32 feature art tile, title RC 18 / 700 upright | description paragraphs R 13, left-bar sub-block with the uses and Current counter (same as in the tab) |
| Skill (Athletics) | provenance "Skills" R 13; row: prof dot (14 px, dark), stat "STR" RC 18 / 700 #75838b, skill name RC 18 / 700, bonus "+6" (sign RC 12) | Customize, one description paragraph |
| Saving throw (Strength) | provenance "Saving Throws"; ability icon (about 32 px), "Strength Saving Throw" RC 18 / 700, "+5" smaller grey | thin red-tinted rule, Customize, several rules paragraphs |
| Ability box (Strength) | ability icon + "Strength 16 (+3)" RC 18 / 700 and R 14 | table 314 wide, rows 29-35 tall, 1 px light row rules, left column labels R 13 / 500 (Total Score, Modifier, Base Score, Bonus with indented grey sub-rows for sources, Set Score, Stacking Bonus), values right column R 13 / 500 with a 2 px vertical grey divider; below it two labelled boxes (Other Modifier, Override Score: 90 x 32 rounded inputs, 1 px #d8d8d8); red-tinted rule; description with bold RC 13 sub-headings ("Strength Checks") |
| AC box | title "Armor Class: 13" RC 18 / 700 | list rows: bold number ("10", "+1", "+2") RC 14 / 700, label R 13, grey bracket note "(None)", "(Shield)"; Customize; description |
| HP number (current) | **does not open a panel**: the number turns into an inline number input with a spinner (red 1 px outline). Clicking the title label "HIT POINTS" opens the panel | "HP Management": CURRENT (input) / MAX 52 (26 px) / TEMP (input) with RC 13 / 700 / #75838b labels and a grey "/" R 26; rule; HEALING input (green label RC 10 / 700 #40d250, border green 1 px, value R 28) with a red plus square to its right; NEW HP and NEW TEMP RC 28 / 400 with grey labels; DAMAGE input (label #d24040, red border) with a red minus square; MAX HP MODIFIER and OVERRIDE MAX HP small inputs. **All write data, never clicked** |
| Proficiency Bonus | title "Proficiency Bonus" RC 18 / 700 | only rules text, links in blue (#1c9aef) |
| Speed | title "Speed" | one row "Walking **30** ft." then Customize and rules text |
| Passive senses | title "Senses" | rows "Passive Perception: **10**", Investigation, Insight, "Darkvision **60** ft." (R 14, values RC/R 14 / 700), Customize, then rules text with bold sub-heads |
| Initiative | "Initiative (+1)" | "Initiative Score: **11**", grey "With Advantage (+5): **16**", "With Disadvantage (-5): **6**", then rules text |
| Defenses | "Defenses" | "RESISTANCES" sub-head RC 18-ish / 700 upper, rows with icon, name and grey bracket "(Damage Resistance)", Customize |
| Conditions | "Conditions" | list of conditions, 60 px rows: icon, name R 14, grey toggle switch (never clicked) at right, chevron to expand rules |

Click targets on the sheet: whole row for attack, spell, feature, skill, save; the ability box; the AC shield; the three passive pills; the prof and speed boxes; initiative; defenses / conditions halves. The Heroic Inspiration box toggles a value, we did not click it.

---------------------------------------------------------------------------------------------------

## 10. Hover and active states (what we could see)

| Element | Normal | Hover | Active |
|---|---|---|---|
| Primary tab | #75838b | no colour change, cursor pointer | #12181c + 3 px theme underline |
| Filter pill | bg #ecedee / text #75838b | bg #525c63 / text #ecedee | bg theme red / text #f9fafa |
| Spell / item / attack / skill / feature row | transparent | **no visible background change**, cursor pointer only | the opened row gets no mark |
| Ability / AC / speed boxes | | cursor pointer, no colour change measured | |
| Theme buttons (Manage ...) | white bg, red text, 1 px red border | not captured (assume slight red tint) | solid red variant = Cast |
| Inventory box | white, 1 px #d8d8d8 | | red filled square |

---------------------------------------------------------------------------------------------------

## 11. Header bar of the sheet (desktop)

The bar is 1200 x 100 on a dark strip (full-width, about #2c2c2c / #333) over the page background art; text is white.

| Thing | Measure |
|---|---|
| Portrait | image 60 x 60 at x 10, y 18, border 2 px solid theme red, radius 3 px (the wrapper is 75 x 60). Frame = our own plain 2 px red rounded square |
| Name | x 85, y 15, RC 24 / 400 white |
| MANAGE chip | x 237, y 21, 41 x 22, 1 px theme border, radius 3, text RC 8 / upper white, padding 5 |
| Species + class line | x 85, y 50, RC 12 / 400 / #a2acb2 ("Dragonborn  Paladin 6", two groups 5 px apart) |
| Level line | x 85, y 66, RC 10 / 400 white ("Level 6") |
| SHORT REST button | x 610, y 33, 117 x 29, 1 px theme border, radius 3, padding 5 px 13 px 4, icon left + label RC 13 / 700 / upper white |
| LONG REST button | x 747, y 33, 110 x 29, same style |
| CAMPAIGN pill | x 877, y 33, 166 x 29; "CAMPAIGN:" RC 13 / 700 / upper white then campaign name RC 13 / 400 white; 1 px theme border |
| Launch-game button | x 1043, 43 x 29, 1 px theme border, triangle play icon |
| Campaign list button | next to it, same size, list icon |
| Builder / "anvil" icon | x 1150, y 25, 40 x 40, no border, white icon |
| Collapse chevron of the sidebar | far top right of the window (double chevron, light grey) |

Order from the right edge: builder icon, then campaign group (CAMPAIGN pill + play + list icons), LONG REST, SHORT REST. Buttons are never filled, only outlined in the theme colour.

---------------------------------------------------------------------------------------------------

## 12. Phone layout

**Important:** the window of the Chrome session ignored resize_window (innerWidth stayed 1470 after four tries, outer = inner = 1470 x 770), so the first tab could not be made narrow. A **new** tab (its own window) was resized and reported **innerWidth 500, innerHeight 657** (Chrome will not go narrower than 500 for a normal window; the requested 375/400 was not possible). The phone layout is already active at 500 px (class `ct-character-sheet-mobile`); the real breakpoint is not measured but is above 500 and below the 1470 desktop (the first pass saw it at 400). Values below are at 500 px width. The built-in browser pane at 375 px could not be used because it is not signed in (private sheet, 403).

### Top area
| Thing | Value |
|---|---|
| Site header | 66 tall, sticky, z 1000 (D&D Beyond logo, search, avatar, menu) |
| Character header | fixed at top 66, 500 x 72, bg #333 (rgb 51,51,51), z 100 |
| Portrait | about 44 x 44 with 2 px theme-red border, radius 3, x 8 |
| Name | x 62, y 75, RC 18 / 400 white |
| MANAGE chip | next to the name, RC 8 white, 1 px theme border |
| Species and class | x 62, RC 10 / 400 / #a2acb2; "Level 6" under it RC 10 white |
| Right of header | a small list button (outlined 42 x 28, theme border) at x 358, and the HP box at x 410: 1 px theme border box 80 x 40: "HIT POINTS" RC 7 white / upper, then "70 / 70" RC 20 / 400 (current and max in green #40d250 when healthy, slash white). Note: this box shows max including temporary HP (52 + 18 = 70). Under it a thin outlined bar "HEROIC INSPIRATION" RC 8 white / upper (x 410, y 115, 82 x 17) |
| Stats strip | y 138, 500 x 71, bg #404040, absolute under the header, scrolls away with the page top (the header stays fixed). Left to right: PROFICIENCY +3 BONUS (x 8), WALKING 30 ft. SPEED (x 127), INITIATIVE in a 40 x 40 white-outline rounded box with "+1" (x 224), ARMOR 13 CLASS (shield outline, x 330), and two stacked buttons DEFENSES and CONDITIONS (x 422, about 70 x 24, 1 px theme border, RC 10 / 700 white). Label RC 11 / 700 / upper white (Walking label is #75838b, 10 px); numbers R 26 / 500 white, "+" sign R 20 / #75838b, "ft." R 16 / #75838b |
| Campaign row | first row of the Abilities section: full-width box 460 x 28 with "CAMPAIGN: varna campai..." (RC 13, truncated with an ellipsis) and a play button at the right |

### Section menu
- Round button bottom-right: red (theme) circle about 44 px with a 3 x 3 dot-grid icon, at x ~402 to 446, y ~600; to its right a second round button (red, double chevron) that toggles the side panel. At the bottom-left another round red button with a d20 icon (dice).
- Tapping the grid opens a dim overlay (page darkens) with buttons: 226 x 52 each (full-width ones 460 x 50), bg #232b2f, border 2 px solid theme red, radius 4, white text RC 14 / upper with a small white line icon at the left, gap 8, 29 px side margin.
- Order: **ABILITIES, SAVES, SENSES** (full width), then pairs: **SKILLS | ACTIONS**, **INVENTORY | SPELLS**, **FEATURES & TRAITS | PROFICIENCIES & TRAINING**, **BACKGROUND | NOTES**, then **EXTRAS** (full width).
- Only one section is visible at a time; picking one closes the overlay and swaps the section. The scroll position of the page is kept between sections (so reset it to the top when you switch).

### Sections on a phone
| Section | Look |
|---|---|
| Abilities, Saves, Senses | One scrolling page: campaign bar, 3 x 2 grid of the ability boxes (each 81 x 95 at x 43 / 212 / 380, ~115 px row pitch), then a box "SAVING THROWS" (title on TOP here, RC 13 / 700 upper with gear), two columns of 3 save pills, the "+2 on saves (Aura of Protection)" line with a green plus-shield icon, then a box "PASSIVE SENSES" (title on top) with three round-ended number boxes (10 / 8 / 13 in 40 x 30 outlined ovals) in a row and labels PERCEPTION / INVESTIGATION / INSIGHT (RC 10-11 / 700 / upper) under them, then "Darkvision 60 ft." centred |
| Skills | One long list, no header: left dot (proficiency), stat grey RC 12 / 700 upper, name R 14 black, bonus in a rounded 40 x 28 outlined box at the right; thin rules between rows |
| Actions | Same table as desktop but without the table box; the pills row is hidden or scrolls; attack rows 46-60 px; "Actions in Combat" comma list and the action feature text below, full width |
| Inventory | Section title "INVENTORY" (RC 13 / 700 upper with gear) at the centre; MY INVENTORY / PARTY INVENTORY halves, weight row with currency, MANAGE INVENTORY button centred, search row full width, pills in one wrapping row, then the table with the same columns (ACTIVE, NAME, WEIGHT, QTY, COST (GP)) squeezed; NOTES column is dropped |
| Spells | title "SPELLS" with gear, summary row (+2 / +5 / 13), MANAGE SPELLS centred, search row, pills, "1ST LEVEL" + SLOTS boxes, table NAME / TIME / RANGE / HIT / DC / EFFECT (the NOTES column is dropped) |
| Features & Traits | title, pills (ALL, CLASS FEATURES, SPECIES TRAITS, FEATS), same text blocks as desktop at the full 460 width |
| Proficiencies & Training | title with gear, groups ARMOR / WEAPONS / TOOLS / LANGUAGES: label RC 12 / 700 / #75838b upper, items R 12 black under it, thin rules between groups |
| Background | title, pills (ALL, BACKGROUND, CHARACTERISTICS, APPEARANCE), same blocks; the characteristics become a 2-column list: label left bold upper, value right |
| Notes | title, pills (ALL, ORGS, ALLIES, ENEMIES, BACKSTORY, OTHER), the five sections |
| Extras | title, MANAGE EXTRAS centred, search row, empty message |

### What scrolls on a phone
- The whole page scrolls (document height was 2089 on the abilities page); the character header (72) and the site header (66) stay on top while the stats strip scrolls up under them. Each section also lists inside a scroll area that is as tall as the viewport minus the header (several nested overflow containers were found). Section boxes have a theme-red 2 px outline and rounded corners, no inner frame art on phone for lists.
- Round buttons float bottom-left (dice) and bottom-right (menu, side panel).

### Side panel on a phone
- Tapping a spell row opens the same panel at **340 px wide**, full viewport height (657), sliding over the right part of the screen (x 159 to 499 at a 500 px window); the page behind is dimmed (about 50 % grey overlay). It is closed by the round double-chevron button at the bottom right. Content is identical to desktop (see section 9).

---------------------------------------------------------------------------------------------------

## 13. Where the theme colour (#c53131) is used (swap this for our Moss green)

| Use | Property |
|---|---|
| Frame lines of every box (ability, saves, senses, skills, HP, initiative hexagon, AC shield, tab box, defenses/conditions box, side panel) | decorative 2 px outline in the theme colour (SVG/border art) |
| Portrait frame | border 2 px |
| Header buttons (Short Rest, Long Rest, Campaign pill, play, list, Manage chip) | 1 px border (text stays white) |
| Active tab | 3 px bottom border (text stays #12181c) |
| Active filter pill | background fill |
| Section headings in tabs (CLASS FEATURES, 1ST LEVEL, ATTUNEMENT, ORGANIZATIONS, "Paladin Features", "ACTIONS", "MANAGE CUSTOM") | text colour |
| MY INVENTORY active half | text colour and underline |
| Theme buttons (Manage Spells, Manage Inventory, Manage Feats, Manage Extras) | border + text colour; white background |
| Cast / Use button, spell slot button in panel, plus / minus squares, Unequip button | solid background fill |
| Equipped / used squares (inventory active, slot boxes) | filled square in the box |
| Search input focus ring, HP input outline | 1 px outline |
| Proficiency star on weapon masteries, small badges | fill |
| Side-panel pencil (edit) icon, count badge on SPELL SLOT, panel header rule tint | stroke / text |
| Phone: menu buttons | 2 px border (fill stays #232b2f); round floating buttons: solid fill |
| Phone: HP bar | NOT theme: green #40d250 (healthy) text |
| Links in rules text | blue #1c9aef (not theme) |
| Healing / damage labels in HP panel | green #40d250 / red #d24040 (fixed, not theme) |

---------------------------------------------------------------------------------------------------

## 14. Not measured / caveats

- **Phone width**: only 500 px was reachable (see section 12). Nothing was measured at 375 or 400; the first pass's 400 px notes still stand. The first window refused every resize, so the desktop window was left as it was (1470 x 770, not 1470 x 857).
- Cantrips and 3rd-level-plus spell groups (the character has none), spell-attack rows in the spell list (spell attack column Hit/DC for attack spells), and the empty Spells state were not seen.
- Hover colours for ability boxes, saves, theme buttons and the sidebar buttons were not captured as changes (no change found for rows). Transition timings not measured.
- Sidebar panel: exact outline art, corner radius and the emblem shape were estimated from screenshots (about 12 px radius, 2 px).
- Currency manager, Party Inventory, filter funnel dialogs, Manage* dialogs, rest dialogs and the Customize drawers were not opened (they write data or open editors).
- Heroic Inspiration box and Conditions toggles were not clicked (they write data).
- The HP number is an inline input. One click on it focused it (value unchanged: 52 / 52, temp 18).
