import { describeResource } from "../logic/resourceText";
import type { ClassResource, FeatResource, SpeciesResource } from "../types";

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
