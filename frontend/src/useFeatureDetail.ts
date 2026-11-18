import { apiFetch } from "./api/transport";
import type { Lang } from "./copy";
import { withLang } from "./logic/langQuery";
import { MsgError, msg } from "./logic/messages";
import { useLangDetails } from "./useLangDetails";

/** GET /api/features/<id> (a catalog feature id, `trait:<species>:<n>` or `background:<id>`): one feature text. */
export interface FeatureDetail {
  id: string;
  name: string;
  level: number | null;
  className: string | null;
  subclassName: string | null;
  source?: string;
  desc: string[];
  textLang?: "bg" | "en";
}

export async function fetchFeatureDetail(id: string, lang: Lang, signal?: AbortSignal): Promise<FeatureDetail> {
  const resp = await apiFetch(withLang(`/api/features/${encodeURIComponent(id)}`, lang), { signal });
  if (!resp.ok) throw new MsgError(msg("feature.failed", { status: resp.status }));
  return (await resp.json()) as FeatureDetail;
}

export const useFeatureDetails = () => useLangDetails<FeatureDetail>(fetchFeatureDetail);
