import { describe, expect, it } from "vitest";
import { cacheFor, cachePut, emptyCache } from "./langCache";

describe("langCache", () => {
  it("shows only the entries of the current language", () => {
    let c = emptyCache<string>("bg");
    c = cachePut(c, "bg", "fireball", "огнена топка", "bg");
    expect(cacheFor(c, "bg")).toEqual({ fireball: "огнена топка" });
    expect(cacheFor(c, "en")).toEqual({});
  });
  it("starts over when the first write after a switch is for the new language", () => {
    let c = cachePut(emptyCache<string>("bg"), "bg", "fireball", "bg text", "bg");
    c = cachePut(c, "en", "fireball", "en text", "en");
    expect(cacheFor(c, "en")).toEqual({ fireball: "en text" });
    expect(cacheFor(c, "bg")).toEqual({});
  });
  it("drops a response that arrives after the language changed", () => {
    const c = cachePut(emptyCache<string>("en"), "bg", "fireball", "late bg text", "en");
    expect(cacheFor(c, "en")).toEqual({});
    expect(cacheFor(c, "bg")).toEqual({});
  });
});
