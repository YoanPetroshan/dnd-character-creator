/** Bulgarian messages for failed API calls. The server's JSON errors are in
 *  English; they are kept only as a secondary technical line after the
 *  Bulgarian text. */
export function httpErrorMessage(status: number, detail = ""): string {
  let base: string;
  if (status === 400) base = "Черновата не е във вярна форма и сървърът я отхвърли.";
  else if (status === 413) base = "Черновата е твърде голяма за сървъра (над 1 MB).";
  else if (status === 500) base = "Сървърът има вътрешна грешка. Опитай пак след малко.";
  else if (status === 502 || status === 503 || status === 504) base = `Няма връзка със сървъра (${status}).`;
  else base = `Сървърът върна грешка ${status}.`;
  return detail ? `${base} Технически детайл: ${detail}` : base;
}
