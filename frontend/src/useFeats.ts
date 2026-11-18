import { apiFetch } from "./api/transport";
import type { Lang } from "./copy";
import { withLang } from "./logic/langQuery";
import { MsgError, msg } from "./logic/messages";

/** GET /api/feats/<id>: what the feat eye shows. Name and prerequisite stay English; `desc` follows `lang`. */
export interface FeatDetail {
  id: string;
  name: string;
  prerequisite: string;
  desc: string[];
  textLang?: "bg" | "en";
}

export async function fetchFeatDetail(id: string, lang: Lang, signal?: AbortSignal): Promise<FeatDetail> {
  const resp = await apiFetch(withLang(`/api/feats/${encodeURIComponent(id)}`, lang), { signal });
  if (!resp.ok) throw new MsgError(msg("feat.failed", { status: resp.status }));
  return (await resp.json()) as FeatDetail;
}
