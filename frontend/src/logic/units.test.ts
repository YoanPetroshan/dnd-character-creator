import { describe, expect, it } from "vitest";
import { formatWeight, formatWeightPair, kilograms } from "./units";
import { bg } from "../copy/bg";
import { en } from "../copy/en";

describe("kilograms", () => {
  it.each([
    [0, "0"], [0.5, "0,2"], [1, "0,5"], [2.5, "1,1"], [5, "2,3"], [10, "4,5"], [22, "10"], [50, "22,7"], [58.5, "26,5"],
    [96, "43,5"], [100, "45,4"], [130, "59"], [225, "102,1"], [1000, "453,6"], [12345, "5599,6"], [-5, "-2,3"],
  ])("%s lb = %s kg (one decimal, decimal comma, a trailing ,0 dropped)", (lb, kg) => {
    expect(kilograms(lb)).toBe(kg);
  });
});

describe("formatWeight", () => {
  it("English: pounds only", () => {
    expect(formatWeight(96, "en")).toBe("96 lb");
    expect(formatWeight(2.5, "en")).toBe("2.5 lb");
    expect(formatWeightPair(96, 225, "en")).toBe("96/225 lb");
  });
  it("Bulgarian: the kilograms follow in brackets", () => {
    expect(formatWeight(96, "bg")).toBe("96 lb (43,5 kg)");
    expect(formatWeight(0, "bg")).toBe("0 lb (0 kg)");
    expect(formatWeight(0.5, "bg")).toBe("0.5 lb (0,2 kg)");
    expect(formatWeight(2.5, "bg")).toBe("2.5 lb (1,1 kg)");
    expect(formatWeight(1000000, "bg")).toBe("1000000 lb (453592,4 kg)");
    expect(formatWeightPair(96, 225, "bg")).toBe("96/225 lb (43,5/102,1 kg)");
  });
  it("a non-finite number is left alone", () => {
    expect(formatWeight(NaN, "bg")).toBe("NaN lb");
  });
  it("stripping the Bulgarian fragment gives the English text", () => {
    const frag = / \(-?\d+(?:,\d)?(?:\/-?\d+(?:,\d)?)? kg\)/;
    for (const lb of [0, 0.5, 2.5, 96, 225.5, 4000]) expect(formatWeight(lb, "bg").replace(frag, "")).toBe(formatWeight(lb, "en"));
  });
  it("the copy catalogs use the helper (EN pounds only, BG with kilograms)", () => {
    expect(en.common.pounds(96)).toBe("96 lb");
    expect(bg.common.pounds(96)).toBe("96 lb (43,5 kg)");
    expect(en.exportPage.carrying(96, 225, 450)).toBe("Carrying: 96/225 lb (push/drag/lift 450 lb)");
    expect(bg.exportPage.carrying(96, 225, 450)).toBe("Carrying: 96/225 lb (43,5/102,1 kg) (push/drag/lift 450 lb (204,1 kg))");
  });
});
