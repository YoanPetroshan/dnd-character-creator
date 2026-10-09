import type { ClassResource } from "../types";

const RECHARGE: Record<string, string> = {
  long: "дълга почивка",
  short: "кратка почивка",
  "short-or-long": "кратка или дълга почивка",
};

/** One resource as text, same wording as the exports: "Rage: 3 (дълга почивка), щета +2". */
export function describeResource(r: ClassResource): string {
  const parts: string[] = [];
  if (r.unlimited) parts.push("без ограничение");
  else if (r.uses != null) parts.push(String(r.uses));
  if (r.die) parts.push(r.die);
  if (r.dice) parts.push(r.dice);
  if (r.pool != null) parts.push(`пул ${r.pool}`);
  if (r.bonus != null) parts.push(`бонус +${r.bonus}`);
  if (r.dc != null) parts.push(`ТС ${r.dc}`);
  let core = parts.join(", ");
  const word = r.recharge ? RECHARGE[r.recharge] : undefined;
  if (word) core = core ? `${core} (${word})` : `(${word})`;
  const damage = r.details?.damageBonus;
  if (typeof damage === "number") core += `, щета +${damage}`;
  const heal = r.details?.heal;
  if (typeof heal === "string") core += `, лекуване ${heal}`;
  return core ? `${r.name}: ${core}` : r.name;
}

/** A plain list of class resources; renders nothing when there are none. */
export function ClassResourcesList({ resources }: { resources: ClassResource[] }) {
  if (resources.length === 0) return null;
  return (
    <ul>
      {resources.map((r) => (
        <li key={r.id}>{describeResource(r)}</li>
      ))}
    </ul>
  );
}
