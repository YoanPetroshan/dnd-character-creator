// The request-body guards of the offline engine (VF7.6). The Flask server refuses a body over 1 MB (413) and the service a body
// nested deeper than 64 levels (400, server/service.py `MAX_JSON_DEPTH`); the offline worker has no Flask in front of it, so
// engineCore checks both here, BEFORE the bytes are copied into WebAssembly (a long run of `[` would overflow the parser's
// stack there), and hands the verdict to the service as a `body_problem` so the two draft routes answer exactly like the
// server: after their `lang` check, with the same JSON `{error}` bodies. Keep the numbers equal to server/service.py
// (a vitest test reads them from there).

export const MAX_BODY_BYTES = 1_000_000;
export const MAX_JSON_DEPTH = 64;

export type BodyProblem = "too-large" | "too-deep";

/** Whether the raw JSON text nests brackets deeper than `limit` (strings skipped, the text is not parsed). A byte scan: the
 *  quote and backslash bytes never occur inside a UTF-8 multi-byte sequence. Stops at the first excess. */
export function jsonDepthExceeds(bytes: Uint8Array, limit: number = MAX_JSON_DEPTH): boolean {
  let depth = 0;
  let inString = false;
  let escaped = false;
  for (let i = 0; i < bytes.length; i++) {
    const ch = bytes[i];
    if (inString) {
      if (escaped) escaped = false;
      else if (ch === 0x5c) escaped = true;
      else if (ch === 0x22) inString = false;
    } else if (ch === 0x22) {
      inString = true;
    } else if (ch === 0x7b || ch === 0x5b) {
      if (++depth > limit) return true;
    } else if (ch === 0x7d || ch === 0x5d) {
      depth--;
    }
  }
  return false;
}

/** What is wrong with a request body, or null. The size comes first (as in Flask, which never reads a body that large). */
export function bodyProblem(body: Uint8Array | null): BodyProblem | null {
  if (!body) return null;
  if (body.byteLength > MAX_BODY_BYTES) return "too-large";
  return jsonDepthExceeds(body) ? "too-deep" : null;
}
