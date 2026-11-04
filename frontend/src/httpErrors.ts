import { msg, type Msg } from "./logic/messages";

/** Message for a failed API call (rendered with the catalog). The server's JSON errors are in
 *  English; they are kept only as a secondary technical line after the localized text. */
export function httpErrorMessage(status: number, detail = ""): Msg {
  let base: Msg;
  if (status === 400) base = msg("http.400");
  else if (status === 413) base = msg("http.413");
  else if (status === 500) base = msg("http.500");
  else if (status === 502 || status === 503 || status === 504) base = msg("http.gateway", { status });
  else base = msg("http.other", { status });
  return detail ? msg("http.detail", { base, detail }) : base;
}
