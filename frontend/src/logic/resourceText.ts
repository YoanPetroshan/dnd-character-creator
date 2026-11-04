import type { Copy } from "../copy";
import type { ClassResource, FeatResource, SpeciesResource } from "../types";

type AnyResource = ClassResource | FeatResource | SpeciesResource;

/** Short fragments for a resource's `details` (mirrors server/export_fields.py `resource_detail_parts`). */
function detailParts(t: Copy, d: Record<string, unknown> | undefined): string[] {
  if (!d) return [];
  const x = t.sheet.resources.text;
  const parts: string[] = [];
  const res = d.resistances;
  if (Array.isArray(res) && res.length > 0) {
    if (res.length === Object.keys(x.damageTypes).length - 1 && !res.includes("psychic")) parts.push(x.resistancesAllButPsychic);
    else parts.push(x.resistances(res.map((r) => x.damageTypes[String(r)] ?? String(r))));
  }
  if (typeof d.shortRestRegains === "number" && d.shortRestRegains > 0) parts.push(x.shortRestRegains(d.shortRestRegains));
  if (d.spellSlotRegainsUse) parts.push(x.spellSlotRegainsUse);
  if (d.bonusActionRegainsOne) parts.push(x.bonusActionRegainsOne);
  if (d.onShortRest) parts.push(x.onShortRest);
  if (typeof d.maxSlotLevel === "number") parts.push(x.maxSlotLevel(d.maxSlotLevel));
  const costs = d.slotCosts;
  if (costs && typeof costs === "object")
    parts.push(
      Object.keys(costs)
        .sort((a, b) => Number(a) - Number(b))
        .map((lvl) => x.slotCost(lvl, (costs as Record<string, number>)[lvl]))
        .join(", "),
    );
  if (typeof d.damageTypes === "string" && d.damageTypes) parts.push(x.damageTypesLine(d.damageTypes));
  if (typeof d.knownForms === "number") parts.push(x.knownForms(d.knownForms));
  if (d.fly === true) parts.push(x.fly);
  if (d.swim === true) parts.push(x.swim);
  const meta = d.metamagic;
  if (Array.isArray(meta) && meta.length > 0)
    parts.push(x.metamagic(meta.map((m: { name: string; cost: number }) => `${m.name} (${m.cost})`).join(", ")));
  const options = d.perRageOptions;
  if (Array.isArray(options) && options.length > 0)
    parts.push(x.perRageOptions(options.map((o: { name: string; effect: string }) => `${o.name}: ${o.effect}`).join("; ")));
  return parts;
}

/** One resource as text: "Rage: 3 (дълга почивка), щета +2". */
export function describeResource(t: Copy, r: AnyResource): string {
  const x = t.sheet.resources.text;
  const parts: string[] = [];
  if (r.unlimited) parts.push(x.unlimited);
  else if (r.uses != null) parts.push(String(r.uses));
  if (r.die) parts.push(r.die);
  if (r.dice) parts.push(r.dice);
  if (r.pool != null) parts.push(x.pool(r.pool));
  if (r.bonus != null) parts.push(x.bonus(r.bonus));
  if (r.dc != null) parts.push(x.dc(r.dc));
  let core = parts.join(", ");
  const word = r.recharge ? x.recharge[r.recharge] : undefined;
  if (word) core = core ? `${core} (${word})` : `(${word})`;
  const note = r.details?.note;
  if (typeof note === "string") core = core ? `${core}, ${note}` : note;
  const damage = r.details?.damageBonus;
  if (typeof damage === "number") core += `, ${x.damageBonus(damage)}`;
  const heal = r.details?.heal;
  if (typeof heal === "string") core += `, ${x.heal(heal)}`;
  for (const fragment of detailParts(t, r.details)) core = core ? `${core}, ${fragment}` : fragment;
  const maxCr = r.details?.maxCr;
  if (typeof maxCr === "string") core = core ? `${core}, ${x.maxCr(maxCr)}` : x.maxCr(maxCr);
  return core ? `${r.name}: ${core}` : r.name;
}
