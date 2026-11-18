import { apiFetch } from "./api/transport";
import type { Lang } from "./copy";
import { withLang } from "./logic/langQuery";
import { MsgError, msg } from "./logic/messages";

interface NamedRef {
  ability_score?: { name: string };
  option_type?: string;
  string?: string;
  bonus?: number;
  name?: string;
}

interface PickOf {
  choose: number;
  from: { options?: NamedRef[] };
}

/** GET /api/catalog/species/<id>: the catalog record plus the book text (`fluff`: short paragraphs of what the
 *  species is, how it looks and where it comes from; `traitDetails`: every trait with its text). */
export interface SpeciesDetail {
  id?: string;
  name: string;
  size: string;
  size_options: string[];
  speed: number;
  movement: Record<string, number | true>;
  darkvision: number | null;
  ability_bonuses: { ability_score: { name: string }; bonus: number }[];
  ability_bonus_options: PickOf | null;
  resist: string[];
  resist_options: PickOf | null;
  languages: { name: string }[];
  language_options: { choose: number } | null;
  fluff: string[];
  traitDetails: { name: string; desc: string[] }[];
  /** "bg" when `fluff` and the trait descriptions are the Bulgarian text, else "en" (names stay English). */
  textLang?: "bg" | "en";
}

export async function fetchSpeciesDetail(id: string, lang: Lang, signal?: AbortSignal): Promise<SpeciesDetail> {
  const resp = await apiFetch(withLang(`/api/catalog/species/${encodeURIComponent(id)}`, lang), { signal });
  if (!resp.ok) throw new MsgError(msg("species.failed", { status: resp.status }));
  return (await resp.json()) as SpeciesDetail;
}
