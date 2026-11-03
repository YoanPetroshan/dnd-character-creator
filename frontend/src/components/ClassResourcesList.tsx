import type { ClassResource, FeatResource, SpeciesResource } from "../types";

const RECHARGE: Record<string, string> = {
  long: "дълга почивка",
  short: "кратка почивка",
  "short-or-long": "кратка или дълга почивка",
  turn: "на ход",
  combat: "на битка",
  rage: "на ярост",
  other: "виж бележката",
};

/** One resource as text, same wording as the exports: "Rage: 3 (дълга почивка), щета +2". */
const DAMAGE_NAMES_BG: Record<string, string> = {
  acid: "киселинни", bludgeoning: "дробящи", cold: "студени", fire: "огнени", force: "силови",
  lightning: "мълниеносни", necrotic: "некротични", piercing: "пробождащи", poison: "отровни",
  psychic: "психични", radiant: "лъчисти", slashing: "режещи", thunder: "гръмотевични",
};

/** Short Bulgarian fragments for the resource `details` (mirrors server/export_fields.py). */
function detailParts(d: Record<string, unknown> | undefined): string[] {
  if (!d) return [];
  const parts: string[] = [];
  const res = d.resistances;
  if (Array.isArray(res) && res.length > 0) {
    if (res.length === Object.keys(DAMAGE_NAMES_BG).length - 1 && !res.includes("psychic"))
      parts.push("съпротива: всички видове щета освен психична");
    else parts.push("съпротива: " + res.map((t) => DAMAGE_NAMES_BG[String(t)] ?? String(t)).join(", "));
  }
  if (typeof d.shortRestRegains === "number" && d.shortRestRegains > 0)
    parts.push(
      d.shortRestRegains === 1
        ? "1 използване се възстановява при кратка почивка"
        : `${d.shortRestRegains} използвания се възстановяват при кратка почивка`,
    );
  if (d.spellSlotRegainsUse) parts.push("използване се възстановява срещу слот за заклинание");
  if (d.bonusActionRegainsOne) parts.push("бонус действие: връща 1 зар");
  if (d.onShortRest) parts.push("при кратка почивка");
  if (typeof d.maxSlotLevel === "number") parts.push(`слотове до ниво ${d.maxSlotLevel}`);
  const costs = d.slotCosts;
  if (costs && typeof costs === "object")
    parts.push(
      Object.keys(costs)
        .sort((a, b) => Number(a) - Number(b))
        .map((lvl) => `слот ниво ${lvl} за ${(costs as Record<string, number>)[lvl]} т.`)
        .join(", "),
    );
  if (typeof d.knownForms === "number") parts.push(`известни форми: ${d.knownForms}`);
  if (d.fly === true) parts.push("летене");
  if (d.swim === true) parts.push("плуване");
  const meta = d.metamagic;
  if (Array.isArray(meta) && meta.length > 0)
    parts.push("метамагия: " + meta.map((m: { name: string; cost: number }) => `${m.name} (${m.cost})`).join(", "));
  const options = d.perRageOptions;
  if (Array.isArray(options) && options.length > 0)
    parts.push(
      "при всяка ярост една от опциите: " +
        options.map((o: { name: string; effect: string }) => `${o.name}: ${o.effect}`).join("; "),
    );
  return parts;
}

export function describeResource(r: ClassResource | FeatResource | SpeciesResource): string {
  const parts: string[] = [];
  if (r.unlimited) parts.push("без ограничение");
  else if (r.uses != null) parts.push(String(r.uses));
  if (r.die) parts.push(r.die);
  if (r.dice) parts.push(r.dice);
  if (r.pool != null) parts.push(`пул ${r.pool}`);
  if (r.bonus != null) parts.push(`бонус ${r.bonus >= 0 ? "+" : ""}${r.bonus}`);
  if (r.dc != null) parts.push(`ТС ${r.dc}`);
  let core = parts.join(", ");
  const word = r.recharge ? RECHARGE[r.recharge] : undefined;
  if (word) core = core ? `${core} (${word})` : `(${word})`;
  const note = r.details?.note;
  if (typeof note === "string") core = core ? `${core}, ${note}` : note;
  const damage = r.details?.damageBonus;
  if (typeof damage === "number") core += `, щета +${damage}`;
  const heal = r.details?.heal;
  if (typeof heal === "string") core += `, лекуване ${heal}`;
  for (const fragment of detailParts(r.details)) core = core ? `${core}, ${fragment}` : fragment;
  const maxCr = r.details?.maxCr;
  if (typeof maxCr === "string") core = core ? `${core}, макс. CR ${maxCr}` : `макс. CR ${maxCr}`;
  return core ? `${r.name}: ${core}` : r.name;
}

/** A plain list of class resources; renders nothing when there are none. */
export function ClassResourcesList({ resources }: { resources: (ClassResource | FeatResource | SpeciesResource)[] }) {
  if (resources.length === 0) return null;
  return (
    <ul>
      {resources.map((r) => (
        <li key={r.id}>{describeResource(r)}</li>
      ))}
    </ul>
  );
}
