import { apiFetch } from "./api/transport";
import type { Lang } from "./copy";
import { withLang } from "./logic/langQuery";
import { MsgError, msg } from "./logic/messages";
import { useLangDetails } from "./useLangDetails";

/** GET /api/subclasses/<id>: the subclass intro and every feature with its level and text. Names stay English. */
export interface SubclassDetail {
  id: string;
  name: string;
  source?: string;
  ruleset?: string;
  desc: string[];
  features: { id: string; name: string; level: number; desc: string[] }[];
  textLang?: "bg" | "en";
}

export async function fetchSubclassDetail(id: string, lang: Lang, signal?: AbortSignal): Promise<SubclassDetail> {
  const resp = await apiFetch(withLang(`/api/subclasses/${encodeURIComponent(id)}`, lang), { signal });
  if (!resp.ok) throw new MsgError(msg("subclass.failed", { status: resp.status }));
  return (await resp.json()) as SubclassDetail;
}

export const useSubclassDetails = () => useLangDetails<SubclassDetail>(fetchSubclassDetail);
