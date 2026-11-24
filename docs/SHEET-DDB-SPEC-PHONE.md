# Character sheet: D&D Beyond PHONE layout from real iPhone screenshots (read 2026-11-24)

Third pass. Earlier passes: `SHEET-DDB-SPEC.md` (desktop top row, columns, Actions tab) and `SHEET-DDB-SPEC-TABS.md` (tabs, side panel,
header, a 500 px browser window). Same rules: we rebuild shapes, sizes, type and behaviour; we do not copy their logo, images or icons
(icons are described in words). Names RC / R as in the earlier docs where useful, but the phone app uses the iOS system font (looks
like SF Pro; a Roboto-like sans is fine for us).

## 0. Source and how to read the numbers

- 38 screenshots (IMG_1969 ... IMG_2007, IMG_2000 missing) from an **iPhone, 1206 x 2622 px at 3x = 402 x 874 pt**. They are of the
  **native iOS app** (bottom tab bar Library / Listings / Search / Characters / Campaigns), in the app's dark theme with a red accent.
- The pictures were read at 920 x 2000 display size; all point values below = display px x 0.437 (= original px / 3). Every number is
  **estimated by eye**, good to about +/- 2 pt. Type sizes are **estimated from cap height**. Colours are **sampled by eye** (hex is
  approximate). Nothing was measured from computed styles.
- Page margin everywhere: **16 pt** left and right (content column 370 pt wide, x 16 to 386).
- Dark theme colours (by eye): fixed header and stat area slate `#28323c`; page background near black blue `#10151b`; section bar and
  container headers slate `#2a3643`; cards / pills / chips fill `#1f2a36`; hairlines `#28323c`; text white `#ffffff`; secondary text grey
  `#8f9ba6`; accent blue (headings, links, buttons) `#3b9bef`; accent red (equipped, used, dice button) `#b8271d`; temp-HP green `#5fd08e`.

### How the real phone differs from the 500 px browser pass (SPEC-TABS section 12)
| Topic | 500 px browser pass | Real iPhone app |
|---|---|---|
| Frame | web page, site header 66 pt + character header 72 (#333) | native app: iOS status bar, back button + name, floating iOS tab bar at the bottom |
| Stats strip | PROFICIENCY, SPEED, INITIATIVE, ARMOR, DEFENSES + CONDITIONS buttons | **ARMOR, INITIATIVE, portrait, HP box, rest button, settings button, CONDITIONS button**. Proficiency bonus and Speed are NOT in the strip any more (they live inside the sections Proficiencies & Training and Speed & Defenses). Defenses button is gone (section Speed & Defenses instead) |
| Sections | 10 (Abilities/Saves/Senses, Skills, Actions, Inventory, Spells, Features & Traits, Proficiencies & Training, Background, Notes, Extras) | **11**: a new section **Speed & Defenses** sits between Spells and Features & Traits, and the last one is named **Extras: Creatures** |
| Section switch | round button bottom right opens a menu | a **section bar** under the header (title + icon on the left, a 3x3 dot icon and a list icon on the right) opens a full-screen **menu sheet**; swiping left/right switches sections (owner report) |
| Dice | not seen | red round **dice button** floats bottom right above the tab bar on every screen |
| Side panel | 340 pt panel from the right | not opened in any screenshot (tap behaviour unknown) |
| Frame art | 2 px red outline boxes | no red outlines: dark slate ornate frames (abilities, saves, senses) and plain rounded slate boxes elsewhere |

## 1. Screenshot index

| # | File | Shows |
|---|---|---|
| 1 | IMG_1969 | Section Abilities, Saves, Senses at the top (scroll 0): full header with armor, initiative, portrait, HP, rest/settings/conditions; six ability cards; start of Saving Throws; red dice button and tab bar visible |
| 2 | IMG_1970 | Same section scrolled: stat area gone, section bar stuck under the name bar; Saving Throws (6 pills), "2 on saves" note, Senses (3 passive rows), Darkvision |
| 3 | IMG_1971 | The section menu sheet (close X, Edit, 11 rows + View Character on Website), Abilities row highlighted |
| 4 | IMG_1972 | Skills at the top: full header, column titles PIN PROF MOD SKILL BONUS, first 9 skills |
| 5 | IMG_1973 | Skills scrolled to the end (History ... Survival), sticky bar |
| 6 | IMG_1974 | Actions at the top: "ACTIONS . Attacks per Action: 2", attack table (Javelin, Longsword, Shortbow, Spear, start of Unarmed Strike) |
| 7 | IMG_1975 | Actions: end of attack table (Unarmed Strike, Breath Weapon (Fire)), "Actions in Combat", Breath Weapon text with 3 use boxes |
| 8 | IMG_1976 | Actions: Channel Divinity (2 use boxes), Sacred Weapon: Imbue Weapon |
| 9 | IMG_1977 | Actions: Sap (Longsword), Sap (Spear), Unarmed Strike text |
| 10 | IMG_1978 | Actions: end of Unarmed Strike, divider, "BONUS ACTIONS" block (Actions in Combat, Spells list, Divine Sense) |
| 11 | IMG_1979 | Actions: Divine Sense, Draconic Flight (1 use box), Lay On Hands: Heal / Healing Pool text |
| 12 | IMG_1980 | Actions: Lay On Hands counter (minus, 30 / 30, plus, Apply), Purify Poison, "REACTIONS" and "OTHER" starts |
| 13 | IMG_1981 | Actions bottom: Reactions, Other blocks |
| 14 | IMG_1982 | Inventory top: MY / PARTY INVENTORY tabs, weight and currency banner, Manage Inventory, EQUIPMENT (11) container, first items |
| 15 | IMG_1983 | Inventory: equipment rows (Dice Set ... Spear), start of BACKPACK |
| 16 | IMG_1984 | Inventory: end of equipment, BACKPACK (6) header, its rows |
| 17 | IMG_1985 | Inventory: end of backpack, QUIVER (0), ATTUNED ITEMS with first empty slot |
| 18 | IMG_1986 | Inventory: ATTUNED ITEMS (3 empty slots), ITEMS REQUIRING ATTUNEMENT, PARTY ITEMS REQUIRING ATTUNEME... |
| 19 | IMG_1987 | Inventory bottom: remaining attunement text, OTHER POSSESSIONS |
| 20 | IMG_1988 | Spells top: search, level chips, modifier / attack / DC, Manage Spells, 1st Level with 4 slots, first rows |
| 21 | IMG_1989 | Spells: end of 1st level, 2nd Level (2 slots both red), first rows (CAST dimmed) |
| 22 | IMG_1990 | Spells: 2nd level bottom (Find Steed, Zone of Truth, ...) |
| 23 | IMG_1991 | Speed & Defenses: Speed, Defenses, Manage Defenses, Resistances, Immunities, Vulnerabilities |
| 24 | IMG_1992 | Features & Traits top: search, filter chips, CLASS FEATURES, Core Paladin Traits, Lay On Hands |
| 25 | IMG_1993 | Features: Lay On Hands counter, Spellcasting, Weapon Mastery |
| 26 | IMG_1994 | Features: Fighting Style, Paladin's Smite (use box) |
| 27 | IMG_1995 | Features: Channel Divinity, Paladin Subclass |
| 28 | IMG_1996 | Features: Oath of Devotion Spells, Sacred Weapon |
| 29 | IMG_1997 | Features: Ability Score Improvement, Extra Attack, Faithful Steed |
| 30 | IMG_1998 | Features: Aura of Protection, "DRAGONBORN TRAITS" start |
| 31 | IMG_1999 | Features: Size, Speed, Draconic Ancestry, Breath Weapon |
| 32 | IMG_2001 | Features: Breath Weapon (Fire) boxes, Damage Resistance, Darkvision, Draconic Flight start |
| 33 | IMG_2002 | Features: Draconic Flight box, "FEATS" with Manage Feats, Ability Score Improvement |
| 34 | IMG_2003 | Features bottom: feats with "From Paladin / From Soldier" |
| 35 | IMG_2004 | Proficiencies & Training: +3 PROFICIENCY BONUS, Manage Proficiencies, Armor / Weapons / Tools / Languages |
| 36 | IMG_2005 | Background: Soldier, ability improvements, CHARACTERISTICS list |
| 37 | IMG_2006 | Background: Personality Traits, Ideals, Bonds, Flaws, "APPEARANCE" start |
| 38 | IMG_2007 | Notes: Organizations, Allies, Enemies, Backstory, Other |

The section order of the screenshots follows the menu order, so the owner very likely swiped (or tapped) through the sections in turn.
**Not captured:** the Extras: Creatures section, any swipe in motion, the HP / conditions / rest / settings / defenses sheets, any item,
spell or skill detail view, the Party Inventory tab, the Skills sort/pin states, light theme, landscape.

## 2. Fixed parts

### 2.1 Layers from top to bottom (402 x 874 pt, all y in pt from the top of the screen)
| Layer | y | Scrolls? |
|---|---|---|
| iOS status bar (time left, mute icon, signal, wifi, battery 63 %) | 0-59 | fixed (system) |
| **Name bar**: back button, name, "Species Class Level" | 59 (bg from 0) to 116 | **fixed** (bg `#28323c`, bottom edge 116) |
| **Stat area** (armor, initiative, portrait, HP, buttons) | 116-244 | **scrolls away** with the content |
| **Section bar** | 259-299 at scroll 0, then **sticks at 131-170** | **sticky** 15 pt under the name bar |
| Section content | below the bar | scrolls under the name bar and the sticky bar (content is visible through the 15 pt gap between name bar and section bar, and is hidden under the bar itself) |
| Floating dice button (red circle 50 pt, centre x 361, y 750; right margin 16) | 725-775 | fixed, above the content |
| Floating iOS tab bar (pill) | 792-852 | fixed |

Only the stat area moves with scroll. Name bar, section bar, dice button and tab bar never move. Inside Inventory a second sticky row
(MY INVENTORY / PARTY INVENTORY tabs, 17 pt under the section bar, y ~190-233) also stays while the list scrolls under it.

### 2.2 Name bar (0-116)
- Back button: circle 44 pt, x 16-60, centre y 84, bg slate lighter `#46525e`, 1 pt lighter ring, white chevron "<" (about 16 pt).
- Name: centred, white, regular, about 17-18 pt (estimated), centre y 77. The sample name is a long single word in Cyrillic; no truncation seen.
- Sub line: centred under it, centre y 93, grey `#8f9ba6`, semibold about 13 pt: "Species Class Level" (e.g. "Dragonborn Paladin 6"). No separate "Level" line.
- No portrait, no HP in the bar.

### 2.3 Stat area (116-244, bg same slate as the name bar, bottom edge at y 244 where the page turns dark)
Two rows, four columns. Row 1 (y 121-178) and row 2 (y 200-236).

| Element | Box (x, y, w x h pt) | Content and type (estimated) |
|---|---|---|
| ARMOR CLASS | x 23-69, y 121-178 | small shield outline (dark slate, lighter stroke) 46 x 46; label **ARMOR** above (caps, bold, white, about 11 pt, y 127); number **13** centred in the shield (bold, about 26 pt, y 148); label **CLASS** below (same caps, y 172). Label sits above/below the shape, not inside |
| INITIATIVE | x 84-135, y 122-166 | hexagon with a point at top and bottom (51 x 44), slate fill, light stroke; value **+1** (bold 26 pt, sign slightly smaller and grey-white); label **INITIATIVE** below at y 172 (same caps, same baseline as CLASS) |
| Portrait | x 158-244 (87), y 121-208 (86) | square image, radius 8, 2 pt light-grey ring (`#6f7d89`). A small circle badge (22 pt, grey `#8f9ba6`, icon = a half sun on a horizon) overlaps the bottom centre edge: this is **Heroic Inspiration** |
| HEROIC INSPIRATION label | centred under portrait, y 221 and 233 | two lines, caps, white, bold about 11 pt: "HEROIC" / "INSPIRATION" |
| HIT POINTS box | x 262-386 (124), y 122-178 (56) | bg near black `#10161c`, radius 6. "HIT POINTS" caps bold white 11 pt centred at y 134; value line y 151: **52/52** white medium about 20 pt, then **(18)** in green `#5fd08e` (temporary HP in brackets, only shown when > 0). Under it a 3 pt bar x 270-378, y 166: blue `#3b7bd6` for current HP, with a green `#4fc98a` stretch at the right end for temp HP |
| Rest button | x 16-76 (60), y 200-236 (36) | near-black `#10161c`, radius 6; icon only: a campfire. (Assumed: opens short/long rest. Not opened in screenshots) |
| Settings button | x 80-140 (60), y 200-236 | same style; icon only: a cog. (Not opened) |
| CONDITIONS button | x 262-386 (124), y 200-236 | same dark box, text **CONDITIONS** white, caps, bold about 13 pt, centred |

Gaps: 4 pt between the two small buttons; the portrait column is centred on the screen (x 201). Armor and initiative are left of the
portrait, HP and conditions right. No proficiency bonus, speed, or defenses button here.

### 2.4 Section bar (the "abilities, saves, senses" row)
- Box: x 16-386 (370), height **40**, radius about 5, bg `#2a3643`. At scroll 0 at y 259-299, sticky at y 131-171.
- Left: section **icon** (white, 18 pt, x 33-51; different icon per section, see section 3), title at x 58, white, semibold, about
  16 pt (estimated; "Abilities, Saves, Senses", "Skills", "Speed & Defenses", ... exactly the menu names, but see below for
  differences), vertically centred.
- Right: a darker segment (`#232e3a`, x 326-386, 60 pt wide, full bar height, a thin vertical seam at x 326) holding a **list icon**
  (white outline, 18 x 18: a stack of two rounded bars with three small bullets to the left, like "list/outline"). The **3 x 3 dot icon**
  sits just left of the seam: nine **red** (`#c8352b`) squares, each about 5 pt with 2 pt gaps, block 18 x 18, x 292-310, centred in the bar.
- **The nine squares look identical (all red, all filled) on every one of the 11 sections.** In the screenshots they do not mark the
  current section: there is no filled-vs-empty difference to read. It is a grid icon. (If the live app dims one square, the screenshots
  do not show it; the pictures were read at reduced size.) Which part opens the menu (whole bar, the dots, or the right segment with
  the list icon) is not visible in the screenshots; the owner says tapping the row opens it, so make the whole bar a button.
- The section title in the bar is the **only** place the current section is named. In the Inventory, Actions etc. there is no second
  title.

### 2.5 Floating dice button
Red `#d3281f` circle 50 pt, centre x 361, y 750 (right margin 16). White line icon of a 20-sided die (icosahedron outline), 22 pt. On
the first screenshot (IMG_1969) the icon is a half-drawn circular arrow (animation frame), on all others the die. Opens a dice roller
(not shown).

### 2.6 iOS tab bar (app navigation, not part of the sheet, but it covers the content)
Floating pill, x 21-381, y 792-852 (60 pt), translucent dark glass over the content (text of the list scrolls visibly under it,
blurred). Five items, icon above label (11 pt): Library (books), Listings (open book), Search (magnifier), **Characters** (selected: red
`#d3281f` icon and label, with a darker pill highlight about x 207-301), Campaigns (flag). Rebuild only if the app wants the same
frame; for our sheet it can be dropped, but keep 60 pt of bottom padding (content scrolls to the very bottom and is covered by the
bar, no inset was added).

## 3. The section switcher

### 3.1 The 11 sections (exact names in the menu, in order)
| # | Menu label | Section bar title | Icon (words) |
|---|---|---|---|
| 1 | Abilities, Saves, Senses | Abilities, Saves, Senses | white owl head |
| 2 | Skills | Skills | three small four-point sparkles |
| 3 | Actions | Actions | a clenched hand with a burst/spiky effect |
| 4 | Inventory | Inventory | a treasure chest |
| 5 | Spells | Spells | a hand with flames |
| 6 | Speed & Defenses | Speed & Defenses | a shield with a vertical split |
| 7 | Features & Traits | Features & Traits | a person head-and-shoulders in a circle |
| 8 | Proficiencies & Training | Proficiencies & Training | a magnifier with an exclamation mark |
| 9 | Background | Background | a quill on a scroll |
| 10 | Notes | Notes | two speech bubbles |
| 11 | Extras: Creatures | (not captured) | a wolf/beast head |

Plus a twelfth row in the menu that is not a section: **View Character on Website** (external-link icon, blue).
**There are 11 sections, not 9.** The "9 squares" are the 3 x 3 dot icon, not 9 pages. The desktop tabs ACTIONS / SPELLS / INVENTORY /
FEATURES & TRAITS / BACKGROUND / NOTES / EXTRAS keep their order; the phone adds Abilities+Saves+Senses, Skills, Speed & Defenses,
Proficiencies & Training and moves the order as in the table (Proficiencies & Training now sits after Features & Traits).

### 3.2 The menu sheet (IMG_1971)
- A **full-screen modal sheet** slides up. It starts at y 62 with a large top radius (about 26 pt) so the dimmed sheet behind (near black)
  shows above it; the status bar stays visible on top. Sheet bg `#2b3641`.
- Top row (y 78-122): **close button** left, a 44 pt circle (x 16-60), bg `#46525e`, white thin X; **Edit** button right, a 62 x 44 pill
  (x 324-386), same grey, text "Edit" white about 17 pt. (Edit probably reorders / hides sections; not opened.)
- List: rows x 32-370 (338 wide, side margin 32), **height 39**, pitch **52** (13 pt gaps), first row top y 142, radius 4. Row bg
  `#212b36` (darker than the sheet). Icon white-grey 18 pt at x 48 (same icon as the section bar), label at x 80, white, semibold, about
  17-18 pt.
- The **current section** row (Abilities in the screenshot) is darker (`#10161c`) with a 1 pt **red** outline (`#b52a22`). All other
  rows have no outline.
- 11 rows + "View Character on Website" occupy y 142 to ~754; the rest of the sheet is empty down to the bottom edge. No scrolling needed
  on this phone.
- Closing: the X button. (Tapping a row almost certainly switches to that section and closes the sheet; the screenshots do not show
  the moment, treat as assumed.)

### 3.3 What changes on a swipe (owner's report, not visible in still screenshots)
Only the area under the section bar moves: a horizontal pager with 11 pages. The name bar and the stat area stay; the section bar stays
(its title and icon change to the new section; the dots do not change). Each page keeps its own vertical scroll. When the page is at
scroll 0 the stat area is visible; when scrolled, only the sticky bar is left under the name bar (see 2.1). Swipe left = next section in
the menu order, swipe right = previous. First section has nothing to the left, last (Extras: Creatures) nothing to the right (assumed).
Within sections with horizontally scrolling chips (Features & Traits filter chips) the chip row scrolls on its own.

## 4. Sections as they look on the phone

General content rules (all sections): left aligned in the 370 pt column; body text about 17 pt regular white, line height about 24 pt
for paragraphs (compact lists 21 pt); **section headings inside a section** in accent blue `#3b9bef`, caps, bold, about 17 pt
("ACTIONS", "BONUS ACTIONS", "REACTIONS", "OTHER", "SPEED", "DEFENSES", "CLASS FEATURES", "DRAGONBORN TRAITS", "FEATS", "BACKGROUND",
"CHARACTERISTICS", "APPEARANCE"); **item headings** bold white about 20-22 pt; grey secondary text `#8f9ba6`; 1 pt hairline dividers `#28323c`
between big blocks; "Manage ..." buttons are centred, text and 1 pt border blue, bg translucent dark, height about 29-31 pt, bold ~17 pt;
**sub-blocks** are marked by a 2 pt grey vertical bar at x 16 and text indented to x 31. Sections have **no panels, accordions or
expanders** in the screenshots: everything is a flat scrolling list (descriptions are always open).

### 4.1 Abilities, Saves, Senses (IMG_1969, 1970)
1. **Ability cards, 3 x 2 grid.** Card 92 x 108 pt, centres x 75 / 201 / 327, row pitch 126 pt, first row top y ~320 (page y), second row top y 445. Dark slate fill `#1f2a38` with an ornate
   frame (`#3a4a5c`): notched top corners, a decorative flourish at the bottom around the score oval. Inside: name in caps, bold,
   white, 14 pt (CONSTITUTION and INTELLIGENCE shrink to about 12 pt to fit), at the top; **modifier box** 65 x 35, radius 4, bg `#252f3b`,
   1 pt lighter border `#4a5a68`, text "+3" semibold about 30 pt (sign same size, slightly dimmer); **score oval** 47 x 26 at the
   bottom overlapping the lower frame, near black `#0c1116`, light ring, score bold about 23 pt. Order: STRENGTH, DEXTERITY, CONSTITUTION /
   INTELLIGENCE, WISDOM, CHARISMA. Whole card is a button (assumed; desktop opens a panel).
2. Hairline divider, then heading **Saving Throws** (white, bold, about 20 pt; note: white here, not blue).
3. **Saving throw pills, 2 columns x 3 rows**, each 176 pt wide (x 16-192 and 209-386), row pitch 66, pill body 40 pt high. Left-to-right
   order in rows: STRENGTH, INTELLIGENCE / DEXTERITY, WISDOM / CONSTITUTION, CHARISMA. A pill = **proficiency marker** at the far left
   (14 pt circle: dashed outline when not proficient, solid white when proficient), a slate bar with a pointed/notched left end holding
   the ability name centred (caps, bold, 14 pt), and at the right a rounded value cap (bulging circle end) with an inner value box
   42 x 28 "+5" (semibold about 22 pt). Proficient in the sample: Wisdom, Charisma.
4. Note line: small green hexagon with a white plus, then "2 on saves (Aura of Protection)" regular 17 pt (the bonus applied to all saves,
   with its source in brackets).
5. Hairline divider, heading **Senses**, then **three passive rows** full width (370 x 40, row pitch 66): at the left a 60 pt round
   cap holding the number (bold about 26 pt), then a long pill with the label in caps bold 15 pt at x 93: PASSIVE PERCEPTION, PASSIVE
   INVESTIGATION, PASSIVE INSIGHT. Then plain text "Darkvision 60 ft." (17 pt) under them.
- Nothing else (no proficiency bonus, no speed) in this section.

### 4.2 Skills (IMG_1972, 1973)
- A column header row (caps, semibold, about 15 pt, grey): **PIN** (x 16), **PROF** (x 59-93), **MOD** (x 107-138), **SKILL** (x 166),
  **BONUS** (right aligned to x 386). Hairline under it.
- 18 rows, alphabetical, each **47 pt** high with a hairline between. Columns: **pin icon** (outline push-pin, grey, 16 pt at x 20-33; tap
  pins the skill, assumed), **prof marker** at x 76 (dashed circle = not proficient, solid white circle = proficient, 14 pt), **MOD** ability
  abbreviation centred at x 122 (DEX WIS INT STR CHA; white regular 17 pt, not grey like desktop), **skill name** at x 166 (white, 17-18 pt),
  **bonus box** at the right x 341-386 (45 x 29, radius 4, 1 pt border `#5a6a7a`, text "+1" / "-2" about 18 pt; plain "-" sign for negatives).
- Rows in order (stat, bonus): Acrobatics DEX +1, Animal Handling WIS +0, Arcana INT -2, Athletics STR +6 (prof), Deception CHA +2,
  History INT -2, Insight WIS +3 (prof), Intimidation CHA +5 (prof), Investigation INT -2, Medicine WIS +0, Nature INT -2, Perception WIS +0,
  Performance CHA +2, Persuasion CHA +5 (prof), Religion INT -2, Sleight of Hand DEX +1, Stealth DEX +1, Survival WIS +0.
- Passive scores are NOT on this page (they are in Senses).

### 4.3 Actions (IMG_1974 to 1981)
One long scroll, no filter pills, no search (the desktop pills ALL / ATTACK / ACTION ... are gone). Blocks in order:
1. Heading row **ACTIONS** (blue caps bold) then a white bullet and **Attacks per Action: 2** (bold white).
2. **Attack table.** Column titles (caps, grey, semibold 15 pt): RANGE (left at x 50), HIT/DC (centred x 218), DAMAGE (right aligned). Hairline.
   Each row is 83 pt high (104 pt when the weapon has a second damage line), hairline between rows:
   - Left column x 16-35: a weapon-kind icon vertically centred: crossed swords (melee weapon), bow with arrow (ranged), fist (unarmed),
     crossed swords again for Breath Weapon. A small **red star** above the icon when the weapon has a **mastery** the character uses.
   - Column x 51: line 1 **name** (white, about 20 pt, regular); line 2 **kind** in caps grey 13 pt, e.g. "MELEE WEAPON", with a small red bullet
     and "MASTERY" appended when mastery applies ("MELEE WEAPON . MASTERY"), "RANGED WEAPON", "MELEE ATTACK"; line 3 **range**: bold number then grey
     long range in brackets ("30 (120)", "80 (320)", "20 (60)") or "5 FT. REACH" (number bold white 20 pt, "FT. REACH" small caps grey 13 pt).
   - Middle: **hit box** x 163-274 (111 wide), 29 high (50 high when there are two damage lines, stretching over both), radius 4, 1 pt border
     `#5a6a7a`, "+6" about 18 pt centred.
   - Right: **damage box** x 314-386 (72 wide, 29 high, same border), dice text about 18 pt ("1d6+3") and a small damage-type icon right of it
     (piercing, slashing, bludgeoning, fire, shown white). A second **versatile damage** box below (x 322-386, 24 high, text grey, no icon).
   - Breath Weapon (Fire) row: range column shows "--", hit/DC column shows a small grey "DEX" and white "13" (the save DC), damage box "2d10" + flame icon.
   - Unarmed Strike damage is a flat "4" with a fist-impact icon.
   - Order in the sample: Javelin, Longsword (1d8+3 / versatile 1d10+3), Shortbow, Spear (1d6+3 / 1d8+3), Unarmed Strike, Breath Weapon (Fire).
3. **Actions in Combat** (bold white 20 pt) with a 2 pt grey bar block holding a comma list in 17 pt: "Attack, Dash, Disengage, Dodge, Grapple, Help, Hide, Improvise,
   Influence, Magic, Ready, Search, Shove, Study, Utilize".
4. **Action features** as headings (bold 20 pt) + full descriptions (17 pt): Breath Weapon (Fire), Channel Divinity, Sacred Weapon: Imbue Weapon,
   Sap (Longsword), Sap (Spear), Unarmed Strike. Bold numbers inside text (DC **13**, **2d10**). Bold-italic run-in heads ("Sap.", "Damage.", "Grapple.", "Shove.").
   **Use counters** under a feature: label "Used Charges:" (17 pt), then empty boxes 28 x 28, radius 4, 1 pt border `#6b7886`, fill `#232d38`, 8 pt gap
   (3 boxes for Breath Weapon, 2 for Channel Divinity, 1 for Draconic Flight); under them an italic grey line with a small filled info icon: "Resets on Long Rest".
5. Hairline, **BONUS ACTIONS** (blue). Inside: "Actions in Combat" (Two-Weapon Fighting); **Spells** sub-heading (bold 20 pt) with one italic line per prepared
   bonus-action spell ("Divine Smite (1ST)" x3, "Shield of Faith" + concentration diamond + "(1ST)"; level in small caps grey); then features Channel
   Divinity: Divine Sense, Draconic Flight (1 box), Lay On Hands: Heal, Lay On Hands: Healing Pool, Lay On Hands: Purify Poison.
   **Counter with steppers** (Healing Pool): label "Available Charges:", then **minus** (28 x 28 red `#c0281e` square, white bar), a **value box** 100 x 28 with a white
   1 pt border showing "**30** / 30" (current bold, max regular), a **plus** (28 x 28, darker red `#7a1f1f` because it is at max), and at the right an **Apply** button
   (100 x 28, dim blue outline and dim text = disabled until the value changes), then "Resets on Long Rest".
6. Hairline, **REACTIONS** (blue): "Actions in Combat" -> "Opportunity Attack". Hairline, **OTHER** (blue): "Actions in Combat" -> "Interact with an Object".
   Nothing after that was captured (bottom hairline visible at the end).

### 4.4 Inventory (IMG_1982 to 1987)
- **Sub-tab row** (sticky under the section bar, y ~190-233, 370 wide): two halves **MY INVENTORY** (active: white, caps, bold 17 pt, 3 pt blue
  `#3b82e6` underline across its half) and **PARTY INVENTORY** (grey). Full-width hairline under the row.
- **Banner** (x 16-386, y ~234-358, 124 high): stone-temple picture background, dark overlay. Left: "WEIGHT CARRIED" caps bold 16 pt grey-white, **116 lb.** (116 about 28 pt
  semibold, "lb." small), "UNENCUMBERED" caps 13 pt. Right: "TOTAL CURRENCY" caps bold with a small blue chevron ">" (opens currency), then a gold coin
  icon and the number **15** (value in gp). Centre bottom: **Manage Inventory** button (145 x 29, blue text/border).
- **Container header** (full width 370, 57 high, bg `#28333f`): "**EQUIPMENT** (11)" (name caps bold about 24 pt, count regular in brackets) and under it the container weight "86 lb." (17 pt).
  The header for the backpack/quiver also has a **red equip square** at its left (28 x 28, `#b8271d` with a white inner square = carried/equipped), text at x 61: "**BACKPACK** (6)", "29 lb. (24/30 lb.)"
  (carried / capacity in grey brackets). Quiver: "QUIVER (0)", "1 lb.".
- **Table**: column titles WEIGHT (x 61), QTY (centred x 223), COST (GP) (right aligned) caps semibold grey 15 pt. Rows 76 pt high with a hairline:
  - col 1 (x 16-44): either a **28 x 28 red square with white inner square** (equipped), an **empty dark outlined square** (can be equipped, is not: Chain Mail), or a grey "--" (not equippable: gear).
  - x 61: name (white, about 20 pt), then caps grey line of tags with red dot separators ("GEAR . HOLY SYMBOL", "HEAVY ARMOR . CHAIN MAIL", "LEGACY . GEAR . TOOL", "GEAR . ADVENTURING GEAR"), then weight "1 lb." (17 pt).
  - qty value centred at x 223 on the weight line ("1", "20", "4"; "--" when none), cost right aligned at x 386 on the same line ("5", "75", "0.5").
  - Equipment rows in the sample: Amulet, Arrows (equipped), Chain Mail (not equipped), Dice Set, Healer's Kit, Javelin (equipped, qty 4), Longsword, Shield, Shortbow, Spear (all equipped), Traveler's Clothes.
    Backpack rows: Blanket, Holy Water, Lamp, Rations (qty 7), Robe, Tinderbox. Alphabetical inside a container.
  - Empty container: grey text "There are no items in this container" (17 pt).
- **Section headers** (full width, 41 high, bg `#252f3b`, text at x 31, caps bold about 20 pt): **ATTUNED ITEMS**, **ITEMS REQUIRING ATTUNEMENT**, **PARTY ITEMS REQUIRING ATTUNEME...** (truncated with an ellipsis,
  one line), **OTHER POSSESSIONS**.
- **Attuned items**: 3 slots (pitch 92 pt): an ornate empty circle 62 pt at the left (thorny ring, slate) and a long pill with the italic grey text "Item not attuned".
- Empty-state lines under headers: "Items that you can attune to will display here as you make them active.", "Party items that you can attune to will display here as you make them active.",
  "+ Add other possessions, treasure, or holdings your character in this section." (a tappable line, grey). 17 pt grey.

### 4.5 Spells (IMG_1988 to 1990)
- **Search field**: x 16-386, 39 high, radius 6, bg `#283440`, magnifier icon at x 33, placeholder "Search in Spells" grey about 19 pt at x 58.
- **Level chips row** (34 high): **All** (active: blue fill `#3b9bef`, white bold ~19 pt, 36 pt wide), **1st**, **2nd** (inactive: bg `#232e3a`, blue bold text, radius 4), and a **concentration filter** chip (diamond with a "C"). Gap 10 pt. One chip per spell level the character has.
- **Summary row** (centred, three groups at x 128 / 204 / 277): "**+2** MODIFIER", "**+5** SPELL ATTACK", "**13** SAVE DC": value semibold about 28 pt (sign dimmer), label caps bold grey 15 pt.
- **Manage Spells** button centred (129 x 29, blue).
- **Level block**: heading "**1st Level**" (bold about 22 pt white) at the left; right side "**SLOTS**" (caps grey 15 pt) and **slot squares** 28 x 28, 8 pt gap, right aligned. **Red filled with white inner square = used**, empty dark square = available. 1st: 4 slots, first used. 2nd: 2 slots, both used (and then every CAST button of that level is shown dimmed = disabled).
- **Table header** (caps grey semibold 15 pt): TIME (centred x 122), RANGE (x 193), HIT/DC (x 264), EFFECT (right). Hairline.
- **Spell row**, 78 pt high with a hairline: line 1 the **name** (white about 22 pt) + optional concentration diamond + **source** in small caps grey 13 pt ("PALADIN", "PALADINS SMITE", "OATH OF DEVOTION SPELLS", blue "U: 1/1" for limited free casts);
  line 2: **CAST** button (69 x 29, 1 pt blue border, blue bold caps ~19 pt; label **USE** for free-use entries; **dimmed** `#243a55` when no slot is left),
  then TIME ("1A", "1BA" = action, bonus action), RANGE ("30 ft." with "ft." smaller, "Self", "Touch"), HIT/DC ("--", or "CHA 13" with small grey CHA), EFFECT right: text ("Buff", "Summoning", "Control") or a **damage box** ("2d8" + radiant burst icon, "3d8", "5" + heart for healing).
  The same spell appears once per source (Divine Smite 3 times at level 1, Find Steed twice). Alphabetical inside a level.
- Level 1 rows: Bless, Divine Smite (Paladin), Divine Smite (Paladin's Smite, U 1/1, USE), Divine Smite (Paladin's Smite, CAST), Protection from Evil and Good, Shield of Faith. Level 2: Aid (5 heart), Bless, Divine Smite x2 (3d8), Find Steed (USE, U 1/1), Find Steed, Protection from Evil and Good, Shield of Faith, Zone of Truth (CHA 13).
- No cantrip chip because none. Spell details open somewhere on tap (not shown).

### 4.6 Speed & Defenses (IMG_1991)
Blue heading **SPEED**; line "Walking: **30** ft." (value bold, "ft." small); hairline; blue **DEFENSES**; centred **Manage Defenses** button (139 x 31); bold headings **Resistances**, **Immunities**,
**Vulnerabilities** (20 pt); under Resistances a row with a flame icon and "Fire" + grey "(Damage Resistance)"; "No Immunities" and "No Vulnerabilities" as plain text. The page is short; the rest is empty.
Conditions are not here: they are the CONDITIONS button in the stat area.

### 4.7 Features & Traits (IMG_1992 to 2003)
- Search field "Search in Features and Traits"; chip row: **All** (active), **Class Features**, **Species Traits**, **Feats** - a **horizontally scrolling** row, the last chip is cut by the screen edge.
- Blue group headings: **CLASS FEATURES**, **DRAGONBORN TRAITS** (species name + TRAITS), **FEATS** (with a centred **Manage Feats** button).
- Class group starts with a bold 24 pt "Paladin Features". Each feature: **title** bold 21 pt + red bullet + grey semibold **source** ("PHB-2024, pg.109"), then the full description; sub-features in a block with the 2 pt grey bar:
  e.g. "Core Paladin Traits" -> Insight, Athletics; "Lay On Hands" with bar block "Lay On Hands: Healing Pool (1 Bonus Action)" (the same Available Charges stepper as in Actions), "Heal (1 Bonus Action)", "Purify Poison (1 Bonus Action)";
  Spellcasting; Weapon Mastery (Longsword (Sap), Spear (Sap) texts and "Sap (Longsword) (1 Action)"); Fighting Style -> "Fighting Style feat . br-2024, pg.110" / Great Weapon Fighting; Paladin's Smite (italic spell lines with "(1ST)" and a "Used Charges" box);
  Channel Divinity (2 boxes); Paladin Subclass -> Oath of Devotion; Oath of Devotion Spells (list of 4 italic spells); Sacred Weapon; Ability Score Improvement; Extra Attack; Faithful Steed; Aura of Protection.
  Species: Creature Type, Size, Speed, Draconic Ancestry (sub block "Gold Dragon"), Breath Weapon (sub block "Breath Weapon (Fire)" with 3 boxes), Damage Resistance (sub "Draconic Resistance (Fire)"), Darkvision, Draconic Flight (1 box).
  Feats: "Ability Score Improvement . PHB-2024, pg.202" with a grey line "From **Paladin**" (From grey, the name bold white), sub list Constitution Score / Strength Score; Great Weapon Fighting (From Paladin); Savage Attacker (From Soldier).
- Source text can wrap to a second line (Aura of Protection line: title + "Aura of Protection Emanation" + source).
- Whole page is expanded, nothing collapses.

### 4.8 Proficiencies & Training (IMG_2004)
Centred **+3** (sign dimmer, about 40 pt) and "PROFICIENCY BONUS" (caps bold 17 pt); **Manage Proficiencies** button (180 x 31); then groups with hairlines between: **Armor** (Heavy Armor, Light Armor, Medium Armor, Shields), **Weapons** (Martial, Simple),
**Tools** (Dice Set), **Languages** (Common, Goblin, Orc). Group heading bold 22 pt; one item per line, 17 pt white, followed by the source in grey brackets "(Paladin)", "(Soldier)", "(Dragonborn)". Line pitch 21 pt.

### 4.9 Background (IMG_2005, 2006)
Blue **BACKGROUND**; bold 24 pt background name "Soldier"; "Soldier Ability Score Improvements . PHB-2024, pg.185" + "From **Soldier**" + bar block with bold "Increase two scores (+2 / +1)", "Constitution Score", "Strength Score"; hairline;
blue **CHARACTERISTICS**; lines "**Alignment:** Chaotic Good", **Gender, Eyes, Size, Height, Faith, Hair, Skin, Age, Weight** (label bold, value regular or grey "--"; line pitch 28 pt); then **Personality Traits**, **Ideals**, **Bonds**, **Flaws**
(bold 20 pt heading + paragraph 17 pt; empty value in grey "No Bonds"); hairline; blue **APPEARANCE** with text (empty state starts "You do not have any appearance ..."). Free text can be in any language (Cyrillic shown).

### 4.10 Notes (IMG_2007)
Bold 24 pt headings with a hairline between each group: **Organizations**, **Allies**, **Enemies**, **Backstory**, **Other**. Empty ones show a grey tappable line "+ Add Organizations", "+ Add Allies", "+ Add Enemies", "+ Add Other".
Backstory shows a **preview** of the text, 3 lines at about 15-16 pt, ended with "..." (tap to open the full note, assumed).

### 4.11 Extras: Creatures
Not in the screenshots. Desktop shows "Extras that you add will display here." when empty; the phone label differs ("Extras: Creatures").

## 5. Interactive things visible, and how they sit on the phone

| Thing | Where / look | Behaviour seen |
|---|---|---|
| HP | stat area, right box 124 x 56: "52/52" and green "(18)", split bar | tapping it is not shown. (Desktop: heal / damage / temp panel.) We keep: box tap opens an HP sheet |
| Heroic Inspiration | grey 22 pt badge on the bottom of the portrait, label under | state shown by the badge (greyed = none); toggling not shown |
| Conditions | wide dark button "CONDITIONS" under HP | opens a list (not shown); when conditions are on the label probably gains a count (unverified) |
| Rest | campfire icon button, left in the second row | assumed rest menu (not shown) |
| Settings | cog icon button | assumed settings (not shown) |
| Dice | red round button floating bottom right | opens roller (not shown); all rows (attacks, skills, saves, hit/DC, damage) are probably tappable for rolls |
| Use counters | boxes 28 pt "Used Charges", empty = unused | tap fills a box (assumed); resets line in italic below |
| Charge pool | minus / value / plus / Apply | minus and plus change the value, Apply commits (plus is dimmed at max, Apply dimmed when unchanged) |
| Spell slots | squares 28 pt, red = used | tap toggles (assumed); CAST dims when all slots used |
| CAST / USE | outlined blue buttons | cast with slot / use a free cast; dim when not castable |
| Equip squares | red = equipped, empty outline = unequipped, "--" = not equippable | tap toggles |
| Skills pin | outline pin icon at the row start | pins skill (assumed) |
| Manage buttons | Manage Inventory / Spells / Defenses / Proficiencies / Feats | open editors (not shown) |
| Filter chips | Spells (All, 1st, 2nd, concentration), Features (All, Class Features, Species Traits, Feats) | one active (blue fill) |
| Search | Spells, Features & Traits | field with magnifier |
| Sub tabs | MY / PARTY INVENTORY | active has blue underline |

## 6. Build notes: the 10 things to get right

1. **11 sections, not 9.** Order: Abilities Saves Senses, Skills, Actions, Inventory, Spells, Speed & Defenses, Features & Traits, Proficiencies & Training, Background, Notes, Extras: Creatures. The nine dots are one 3 x 3 grid icon (all red, never changes).
2. **Three layers that never scroll away**: name bar (to y 116), the section bar (sticky at y 131, 40 high, 15 pt under the name bar) and the floating dice button + bottom bar. Only the stat area (armor, initiative, portrait, HP, buttons) scrolls up with the page.
3. **Section bar anatomy**: 370 x 40, icon + title left, then the 3 x 3 red dots, then a darker 60 pt segment with the list icon. Whole bar opens the menu.
4. **Swipe pager**: a horizontal pager under the sticky bar; header, stat area and bar stay; bar icon + title swap; each page keeps its own scroll; page order = menu order.
5. **Menu sheet**: full-screen modal from y 62, big top radius, X (left) + Edit (right) at the top, rows 339 x 39 with a 13 pt gap, icon + label, current row darker with a 1 pt red outline, "View Character on Website" last.
6. **Stat area layout**: armor shield and initiative hexagon (labels below, same baseline) left of a 87 pt portrait with the inspiration badge on its bottom edge; HP box 124 x 56 and CONDITIONS 124 x 36 on the right; rest and settings icon buttons 60 x 36 under armor/initiative. Proficiency bonus and speed are **not** in the strip.
7. **Dark slate language, no red outlines**: slate `#28323c` / `#2a3643` / `#1f2a36`, near black `#10151b` page, blue `#3b9bef` for headings, buttons and chips, red only for used/equipped squares, the menu current row and the dice button.
8. **Heading system**: blue caps bold section headings, bold white item headings, grey small-caps source/tag lines with red dot separators, 2 pt grey bar for sub-blocks; whole sections are flat and fully open (no accordions).
9. **Row systems**: skills 47 pt rows (pin, prof marker, mod, name, 45 x 29 bonus box); attacks 83 pt rows (icon column with red mastery star, name / kind / range, centred hit box, right damage box, second damage box for versatile); inventory 76 pt rows (equip square, name / tags / weight, qty centred, cost right); spells 78 pt rows (name + source, outlined CAST/USE button, time, range, hit/DC, effect).
10. **Counters and states**: 28 pt use boxes with "Resets on ..." italic line, the red-minus / value box / red-plus / Apply stepper, spell slots red = used with dimmed CAST, prof markers dashed (no) vs solid white (yes), passive and save shapes as notched pills with a round value cap.

## 7. Not shown clearly or not at all
- Extras: Creatures; Party Inventory tab; any tapped state (HP, conditions, rest, settings, dice, details); the exact swipe animation (still images only).
- Whether the 3 x 3 dots ever change (all nine look identical, red, in all 38 pictures); which part of the bar is the menu button.
- Exact fonts (looks like the iOS system font), exact colours and sizes (all estimated), the real stat-area vertical offsets while the page bounces/overscrolls.
- The fixed icons' exact drawings (described in words only) and the ornate frame art of ability, save and senses shapes.
- The bottom of Actions (after "Interact with an Object"), the end of Inventory's "Other possessions", the Background "Appearance" text, and the end of Notes.
