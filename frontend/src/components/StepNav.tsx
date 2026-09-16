import { NavLink } from "react-router-dom";
import { useResolutionContext } from "../ResolutionContext";
import type { ChoiceSourceKind } from "../types";

interface Step {
  path: string;
  label: string;
  kind: ChoiceSourceKind | null;
}

const STEPS: Step[] = [
  { path: "/home", label: "Home", kind: null },
  { path: "/class", label: "Клас", kind: "class" },
  { path: "/background", label: "Background", kind: "background" },
  { path: "/species", label: "Species", kind: "species" },
  { path: "/abilities", label: "Abilities", kind: null },
  { path: "/equipment", label: "Equipment", kind: "equipment" },
  { path: "/export", label: "Export", kind: null },
];

export function StepNav() {
  const { resolution } = useResolutionContext();

  function pendingCount(kind: ChoiceSourceKind | null): number {
    if (!kind || !resolution) return 0;
    return resolution.choices.filter((c) => c.source.kind === kind && c.status === "pending").length;
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
