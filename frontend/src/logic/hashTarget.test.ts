import { describe, expect, it } from "vitest";
import { cidFromHash } from "./hashTarget";

describe("cidFromHash", () => {
  it("returns the cid after the # (colons kept)", () => {
    expect(cidFromHash("#class:warlock:1:eldritch-invocations")).toBe("class:warlock:1:eldritch-invocations");
  });
  it("decodes percent-encoding", () => {
    expect(cidFromHash("#class%3Awarlock%3A1%3Ax")).toBe("class:warlock:1:x");
  });
  it("empty, bare # and malformed encodings give null / the raw text", () => {
    expect(cidFromHash("")).toBeNull();
    expect(cidFromHash("#")).toBeNull();
    expect(cidFromHash("#a%E0%A4%A")).toBe("a%E0%A4%A");
  });
});
