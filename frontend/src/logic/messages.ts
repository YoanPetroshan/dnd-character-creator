// Messages produced by pure modules and hooks (library, draft merge, HTTP errors, export gate).
// They carry a stable code plus parameters and are rendered with the catalog at display time, so a
// language switch re-renders them and no module embeds user-facing text. Server-written messages
// (problems, warnings, pruned reasons) are data and are shown as delivered; they are NOT Msg.
import type { Copy } from "../copy";

type Catalog = Copy["msg"];
export type MsgCode = keyof Catalog;
export type MsgParam = string | number | Msg;
export interface Msg {
  code: MsgCode;
  params?: Record<string, MsgParam>;
}

export const msg = (code: MsgCode, params?: Record<string, MsgParam>): Msg => (params ? { code, params } : { code });

/** An Error that carries a Msg. Its `.message` is the code (a stable English token, never shown). */
export class MsgError extends Error {
  readonly msg: Msg;
  constructor(m: Msg) {
    super(m.code);
    this.name = "MsgError";
    this.msg = m;
  }
}

/** Any thrown value as a Msg: message errors keep their code, other errors show their own (technical) text. */
export function toMsg(err: unknown): Msg {
  if (err instanceof MsgError) return err.msg;
  return msg("raw", { text: err instanceof Error ? err.message : String(err) });
}

/** Render a message with a catalog. Numbers and nested messages in `params` become strings first. */
export function renderMsg(t: Copy, m: Msg): string {
  const params: Record<string, string> = {};
  for (const [k, v] of Object.entries(m.params ?? {})) params[k] = typeof v === "object" ? renderMsg(t, v) : String(v);
  return (t.msg[m.code] as (p: Record<string, string>) => string)(params);
}
