// Bulgarian -> Latin: the official "streamlined system" (Закон за транслитерацията, 2009).
// The Cyrillic table below is a script mapping, not UI text (exception in copyGuards.test.ts).
// Rules: ж zh, ц ts, ч ch, ш sh, щ sht, ъ a, ь y, ю yu, я ya; word-final "ия" -> "ia" ("ий" -> "iy" falls out of
// и + й). Only the first letter of a digraph is capitalised ("Zh"); a word written in capitals keeps all capitals
// ("ЖИВКА" -> "ZHIVKA"). Hyphens, spaces, digits and non-Cyrillic characters pass through unchanged.

const MAP: Record<string, string> = {
  а: "a", б: "b", в: "v", г: "g", д: "d", е: "e", ж: "zh", з: "z", и: "i", й: "y", к: "k", л: "l", м: "m",
  н: "n", о: "o", п: "p", р: "r", с: "s", т: "t", у: "u", ф: "f", х: "h", ц: "ts", ч: "ch", ш: "sh", щ: "sht",
  ъ: "a", ь: "y", ю: "yu", я: "ya", ѝ: "i",
};

const WORD = /[А-Яа-яЍѝ]+/g;

function word(w: string): string {
  const allCaps = w.length > 1 && w === w.toUpperCase();
  let out = "";
  for (let i = 0; i < w.length; i++) {
    const ch = w[i];
    const lower = ch.toLowerCase();
    const isUpper = ch !== lower;
    const finalIa = i === w.length - 2 && lower === "и" && w[i + 1].toLowerCase() === "я";
    const latin = finalIa ? "ia" : MAP[lower];
    out += isUpper ? (allCaps ? latin.toUpperCase() : latin[0].toUpperCase() + latin.slice(1)) : latin;
    if (finalIa) break;
  }
  return out;
}

export function transliterate(text: string): string {
  return text.replace(WORD, word);
}
