import { useEffect, useRef, useState } from "react";
import { useLang, useT } from "../LanguageContext";
import type { Copy, Lang } from "../copy";
import { cacheFor, cachePut, emptyCache, type LangCache } from "../logic/langCache";
import { renderMsg, toMsg, type Msg } from "../logic/messages";
import { fetchItemDetail, type ItemDetail } from "../useItems";

export type ItemDetailState = { status: "loading" } | { status: "error"; message: Msg } | { status: "ready"; item: ItemDetail };

/** Lazily fetched item texts keyed by item id, the app language and the ruleset: `loadDetail(id)` fetches once per
 *  language (a failed fetch may be retried); switching the language hides the other language's texts. */
export function useItemDetails(ruleset: string = "mixed") {
  const { lang } = useLang();
  const [cache, setCache] = useState<LangCache<ItemDetailState>>(() => emptyCache(lang));
  const requested = useRef<{ lang: Lang; ruleset: string; ids: Set<string> }>({ lang, ruleset, ids: new Set() });
  const current = useRef({ lang, ruleset });
  current.current = { lang, ruleset };
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true; // StrictMode runs mount, cleanup, mount
    return () => {
      alive.current = false;
    };
  }, []);

  // The ruleset is part of the cache key: the property and mastery texts differ between 2014 and 2024.
  const key = (id: string) => `${ruleset}|${id}`;

  function loadDetail(id: string) {
    if (requested.current.lang !== lang || requested.current.ruleset !== ruleset) requested.current = { lang, ruleset, ids: new Set() };
    const ids = requested.current.ids;
    if (ids.has(id)) return;
    ids.add(id);
    const put = (state: ItemDetailState) => setCache((c) => cachePut(c, lang, key(id), state, current.current.lang));
    put({ status: "loading" });
    fetchItemDetail(id, lang, ruleset)
      .then((item) => {
        if (alive.current) put({ status: "ready", item });
      })
      .catch((err: unknown) => {
        if (!alive.current) return;
        ids.delete(id); // closing and reopening the card retries
        put({ status: "error", message: toMsg(err) });
      });
  }

  // A card that was opened before a language or ruleset switch is still open: fetch its text again.
  const loadRef = useRef(loadDetail);
  loadRef.current = loadDetail;
  const opened = useRef(new Set<string>());
  useEffect(() => {
    [...opened.current].forEach((id) => loadRef.current(id));
  }, [lang, ruleset]);

  const all = cacheFor(cache, lang);
  return {
    detailOf: (id: string): ItemDetailState | undefined => all[key(id)],
    loadDetail: (id: string) => {
      opened.current.add(id);
      loadDetail(id);
    },
  };
}

const signed = (n: number) => (n >= 0 ? `+${n}` : `${n}`);

interface Fact {
  key: string;
  label: string;
  value: string;
}

/** "5 ft" or "80/320 ft" in the app's unit words. */
function rangeText(t: Copy, r: { normal: number; long?: number | null }): string {
  return r.long ? `${r.normal}/${r.long} ${t.itemDetail.feetShort}` : t.common.feet(r.normal);
}

function costText(t: Copy, c: { quantity: number; unit: string }): string {
  return t.itemDetail.coins[c.unit] ? `${c.quantity} ${t.itemDetail.coins[c.unit]}` : `${c.quantity} ${c.unit}`;
}

/** The quick facts of an item, only those the record has. Item names stay English; the rest is the app language. */
export function itemFacts(t: Copy, item: ItemDetail): Fact[] {
  const d = t.itemDetail;
  const facts: Fact[] = [];
  facts.push({ key: "category", label: "", value: t.equipmentPage.categories[item.category] ?? item.category });
  if (item.cost) facts.push({ key: "cost", label: d.cost, value: costText(t, item.cost) });
  if (item.weight != null) facts.push({ key: "weight", label: d.weight, value: t.common.pounds(item.weight) });
  if (item.damage) {
    const type = item.damage.type ? t.sheet.resources.text.damageTypes[item.damage.type] ?? item.damage.type : null;
    facts.push({ key: "damage", label: d.damage, value: t.sheet.attacks.damage(item.damage.dice, type) });
  }
  if (item.twoHandedDamage) facts.push({ key: "twoHanded", label: d.twoHanded, value: item.twoHandedDamage.dice });
  if (item.range) facts.push({ key: "range", label: d.range, value: rangeText(t, item.range) });
  if (item.throwRange && JSON.stringify(item.throwRange) !== JSON.stringify(item.range)) {
    facts.push({ key: "thrown", label: d.thrown, value: rangeText(t, item.throwRange) });
  }
  if (item.armor) {
    const a = item.armor;
    const base = a.base < 10 ? signed(a.base) : String(a.base);
    facts.push({ key: "ac", label: d.ac, value: a.dexBonus ? `${base}${d.dexMax(a.maxBonus)}` : base });
    if (a.strMinimum > 0) facts.push({ key: "strMin", label: d.strMin, value: String(a.strMinimum) });
    if (a.stealthDisadvantage) facts.push({ key: "stealth", label: d.stealth, value: d.stealthValue });
  }
  return facts;
}

export function ItemDetailBody({ state }: { state: ItemDetailState | undefined }) {
  const t = useT();
  if (!state || state.status === "loading") return <p className="species-eye__status">{t.common.loading}</p>;
  if (state.status === "error") return <p className="species-eye__status">{t.common.errorLine(renderMsg(t, state.message))}</p>;
  const { item } = state;
  const rules = [...item.properties.filter((p) => p.desc.length > 0).map((p) => ({ key: `p:${p.id}`, name: p.name, desc: p.desc })),
    ...(item.mastery && item.mastery.desc.length > 0 ? [{ key: "mastery", name: `${t.itemDetail.mastery}: ${item.mastery.name}`, desc: item.mastery.desc }] : [])];
  return (
    <div className="species-eye__body">
      <p className="species-eye__facts">
        {itemFacts(t, item).map((f) => (
          <span key={f.key} className="species-eye__fact">
            {f.label && <span className="species-eye__fact-label">{f.label}</span>} {f.value}
          </span>
        ))}
      </p>
      {item.desc.map((paragraph, i) => (
        <p key={`d${i}`} className="species-eye__lore">
          {paragraph}
        </p>
      ))}
      {item.special.map((paragraph, i) => (
        <p key={`s${i}`} className="species-eye__lore">
          {paragraph}
        </p>
      ))}
      {item.contents.length > 0 && (
        <p className="species-eye__lore">
          <span className="species-eye__fact-label">{t.itemDetail.contents}</span>{" "}
          {item.contents.map((c) => (c.qty !== 1 ? `${c.name} ×${c.qty}` : c.name)).join(", ")}
        </p>
      )}
      {item.properties.length > 0 && (
        <p className="species-eye__facts">
          <span className="species-eye__fact">
            <span className="species-eye__fact-label">{t.itemDetail.properties}</span> {item.properties.map((p) => p.name).join(", ")}
          </span>
        </p>
      )}
      {rules.length > 0 && (
        <dl className="species-eye__traits">
          {rules.map((r) => (
            <div key={r.key} className="species-eye__trait">
              <dt className="species-eye__trait-name">{r.name}</dt>
              {r.desc.map((line, j) => (
                <dd key={j} className="species-eye__trait-text">
                  {line}
                </dd>
              ))}
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
