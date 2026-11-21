import { describe, expect, it } from "vitest";
import { clampParagraphs } from "./components/FeatureDetailBody";

describe("clampParagraphs (the 'Show more' cut of a long feature text)", () => {
  it("a short text is not cut", () => {
    expect(clampParagraphs(["One. Two."])).toBeNull();
    expect(clampParagraphs(["a".repeat(600)], 520)).toBeNull(); // a little over the limit is not worth a button
  });
  it("a long text keeps the paragraphs that fit", () => {
    const paras = ["a".repeat(300), "b".repeat(300), "c".repeat(300)];
    expect(clampParagraphs(paras, 520)).toEqual([paras[0]]);
  });
  it("one long paragraph is cut at the end of a sentence", () => {
    const sentence = "This is one sentence of the rules text. ";
    const para = sentence.repeat(30);
    const cut = clampParagraphs([para], 520)!;
    expect(cut).toHaveLength(1);
    expect(cut[0].endsWith(".")).toBe(true);
    expect(cut[0].length).toBeLessThanOrEqual(520);
  });
});
