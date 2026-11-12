/** A geometric class mark: a diamond with a motif inside, drawn as inline SVG (decorative, aria-hidden).
 *  The twelve marks are DRAFTS from docs/design-mockups/j-palettes.html; edit only the MOTIFS table to change them.
 *  Any other class id gets the generic mark (an empty diamond with a dot). */
const DIAMOND = "M30 3l24 27-24 27L6 30z";

const MOTIFS: Record<string, string> = {
  // double-headed axe
  barbarian: "M30 17V46M30 21L21 19Q18.5 25 21 31L30 29M30 21L39 19Q41.5 25 39 31L30 29",
  // lyre, strings evenly spaced (22, 26, 30, 34, 38)
  bard: "M22 21v9a8 8 0 0 0 16 0v-9M26 21v14M30 21v15M34 21v14",
  // morningstar: spiked head on a handle
  cleric:
    "M35 24a5 5 0 1 1-10 0a5 5 0 1 1 10 0zM30 29V46M30 19V14M33.5 20.5L37 17M35 24H40M33.5 27.5L37 31M26.5 27.5L23 31M25 24H20M26.5 20.5L23 17",
  // leaf: outline, midrib and diagonal veins up from the midrib
  druid: "M30 16c9 6 9 22 0 28c-9-6-9-22 0-28zM30 20V44M30 37L24 31M30 37L36 31M30 30L25 25M30 30L35 25",
  // two crossed swords
  fighter: "M23 17L35 35M31.3 37.5l7.4-5M35 35l3 4.5M37 17L25 35M28.7 37.5l-7.4-5M25 35l-3 4.5",
  // (draft, owner wants other ideas)
  monk: "M40 30a10 10 0 1 1-20 0a10 10 0 1 1 20 0zM33 30a3 3 0 1 1-6 0a3 3 0 1 1 6 0z",
  // shield with a sun
  paladin:
    "M21 19h18v10c0 8-9 14-9 14s-9-6-9-14zM32.5 28a2.5 2.5 0 1 1-5 0a2.5 2.5 0 1 1 5 0zM30 23.5V21M30 32.5V35M34.5 28H37M25.5 28H23M33.2 24.8L35 23M26.8 24.8L25 23M33.2 31.2L35 33M26.8 31.2L25 33",
  // arrow: head, shaft, fletching
  ranger: "M30 12l-4.5 7h9zM30 19V46M30 38l-4 5M30 42l-4 5M30 38l4 5M30 42l4 5",
  // serrated dagger
  rogue: "M30 12L36 19L33.5 21.5L36 24.5L33.5 27L36 30L34 34H26ZM21 36H39M30 36V44M28 44H32",
  // flame
  sorcerer:
    "M30 14c2 6 9 9 9 18a9 9 0 0 1-18 0c0-4 2-6 4-8c0 3 2 4 3 4c-1-5 0-9 2-14zM30 40a4 4 0 0 1-4-4c0-3 3-4 4-8c1 3 4 5 4 8a4 4 0 0 1-4 4z",
  // eye with a vertical pupil
  warlock: "M17 30q13-12 26 0q-13 12-26 0zM35 30a5 5 0 1 1-10 0a5 5 0 1 1 10 0zM30 26.5V33.5",
  // three nested diamonds (the outline is the outer one), equal gaps, corners joined by straight lines
  wizard: "M30 12l16 18-16 18-16-18zM30 21l8 9-8 9-8-9zM6 30H22M38 30H54M30 3V21M30 39V57",
};

const GENERIC = "M33.5 30a3.5 3.5 0 1 1-7 0a3.5 3.5 0 1 1 7 0z";

export function ClassGlyph({ classId, solid = false }: { classId?: string; solid?: boolean }) {
  return (
    <span className="class-glyph" data-solid={solid ? "true" : undefined} aria-hidden="true">
      <svg viewBox="0 0 60 60" focusable="false">
        <path d={DIAMOND} />
        <path d={(classId && MOTIFS[classId.toLowerCase()]) || GENERIC} />
      </svg>
    </span>
  );
}
