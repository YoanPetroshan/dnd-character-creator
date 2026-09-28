import { NavLink } from "react-router-dom";
import { useResolutionContext } from "../ResolutionContext";
import type { ChoiceSourceKind } from "../types";

interface Step {
  path: string;
  label: string;
  // Most steps only ever show choices of their own kind. The Background
  // step also renders feat-sourced choices (a background-granted feat's
  // proficiency/ability-bonus/language picks — see BackgroundPage.tsx),
  // so its badge count must include "feat" too or it'll undercount. The
  // Class step has the same situation: a feat picked at an ASI slot can
  // cascade its own proficiency/ability-bonus/language sub-choices (see
  // ClassPage.tsx), so it also needs "feat" in its kind list.
  kind: ChoiceSourceKind[] | null;
}

const STEPS: Step[] = [
  { path: "/home", label: "Home", kind: null },
  { path: "/class", label: "Клас", kind: ["class", "feat"] },
  { path: "/background", label: "Background", kind: ["background", "feat"] },
  { path: "/species", label: "Species", kind: ["species"] },
  { path: "/abilities", label: "Abilities", kind: null },
  { path: "/equipment", label: "Equipment", kind: ["equipment"] },
  { path: "/export", label: "Export", kind: null },
];

export function StepNav() {
  const { resolution } = useResolutionContext();

  function pendingCount(kinds: ChoiceSourceKind[] | null): number {
    if (!kinds || !resolution) return 0;
    return resolution.choices.filter((c) => kinds.includes(c.source.kind) && c.status === "pending").length;
  }

  return (
    <nav className="step-nav">
      {STEPS.map((step) => {
        const count = pendingCount(step.kind);
        return (
          <NavLink key={step.path} to={step.path} className={({ isActive }) => (isActive ? "active" : "")}>
            {step.label}
            {count > 0 && <span className="step-nav__badge">{count}</span>}
          </NavLink>
        );
      })}
    </nav>
  );
}
