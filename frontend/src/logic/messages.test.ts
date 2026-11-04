import { describe, expect, it } from "vitest";
import { bg, en } from "../copy";
import { httpErrorMessage } from "../httpErrors";
import { MsgError, msg, renderMsg, toMsg } from "./messages";

describe("renderMsg", () => {
  it("renders a code with parameters, numbers and nested messages included", () => {
    const m = msg("http.detail", { base: msg("http.gateway", { status: 503 }), detail: "upstream" });
    expect(renderMsg(bg, m)).toBe("Няма връзка със сървъра (503). Технически детайл: upstream");
    expect(renderMsg(en, m)).toBe("No connection to the server (503). Technical detail: upstream");
  });

  it("the Bulgarian wording of the HTTP errors is the one the app always had", () => {
    expect(renderMsg(bg, httpErrorMessage(400))).toBe("Черновата не е във вярна форма и сървърът я отхвърли.");
    expect(renderMsg(bg, httpErrorMessage(413))).toBe("Черновата е твърде голяма за сървъра (над 1 MB).");
    expect(renderMsg(bg, httpErrorMessage(500))).toBe("Сървърът има вътрешна грешка. Опитай пак след малко.");
    expect(renderMsg(bg, httpErrorMessage(502))).toBe("Няма връзка със сървъра (502).");
    expect(renderMsg(bg, httpErrorMessage(404))).toBe("Сървърът върна грешка 404.");
    expect(renderMsg(bg, httpErrorMessage(404, "Not Found"))).toBe("Сървърът върна грешка 404. Технически детайл: Not Found");
  });

  it("library notices keep their Bulgarian text (including the odd closing quote after the name)", () => {
    const why = msg("lib.unreadable");
    expect(renderMsg(bg, msg("lib.isolated", { name: "Зара", why, key: "k" }))).toBe(
      'Героят „Зара": Запазената чернова е повредена. Започнат е празен; старият текст е запазен в браузъра (k).',
    );
    expect(renderMsg(bg, msg("lib.isolated", { name: "", why, key: "k" }))).toContain("Героят „Без име\":");
    expect(
      renderMsg(bg, msg("lib.libraryDamaged", { saved: msg("lib.backupFailed"), recovered: msg("lib.startedEmptyLibrary") })),
    ).toBe(
      "Списъкът с герои (библиотеката) е повреден или от по-нова версия. Копие НЕ можа да се запази (хранилището е пълно). Започнато е с празна библиотека.",
    );
    expect(renderMsg(bg, msg("lib.tooMany", { max: 200 }))).toBe("Пакетът е прекалено голям: приемат се най-много 200 героя.");
  });
});

describe("toMsg", () => {
  it("keeps the message of a MsgError and wraps any other error text as a raw message", () => {
    const m = msg("net.offline");
    expect(toMsg(new MsgError(m))).toBe(m);
    expect(renderMsg(en, toMsg(new Error("boom")))).toBe("boom");
    expect(renderMsg(en, toMsg("plain"))).toBe("plain");
  });
});
