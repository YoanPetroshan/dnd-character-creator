import { useEffect, useRef } from "react";
import { NavLink, useLocation } from "react-router-dom";
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
  // A background-granted feat's cascaded choices (cid "feat:{index}:...")
  // and an ASI-selected feat's cascaded choices (cid
  // "class:{clsId}:{lvl}:asi:feat:{index}:...") share source.kind "feat",
  // so the plain `kind` list above can't tell them apart on its own — it
  // would double-count a single choice on BOTH the Class and Background
  // badges. `cidFilter`, when given, additionally requires a choice's id
  // to match before it counts toward this step, mirroring the same cid
  // scoping ClassPage.tsx / BackgroundPage.tsx apply to their own choice
  // lists. Omit it for steps that don't include "feat" in `kind`.
  cidFilter?: (id: string) => boolean;
}

const STEPS: Step[] = [
  { path: "/home", label: "Home", kind: null },
  { path: "/class", label: "Клас", kind: ["class", "feat"], cidFilter: (id) => id.startsWith("class:") },
  { path: "/background", label: "Background", kind: ["background", "feat"], cidFilter: (id) => !id.startsWith("class:") },
  { path: "/species", label: "Species", kind: ["species"] },
  { path: "/abilities", label: "Abilities", kind: null },
  { path: "/equipment", label: "Equipment", kind: ["equipment"] },
  { path: "/export", label: "Export", kind: null },
];

export function StepNav() {
  const { resolution } = useResolutionContext();
  const navRef = useRef<HTMLElement>(null);
  const { pathname } = useLocation();

  // Keep the active step visible when the nav scrolls horizontally on phones.
  useEffect(() => {
    navRef.current?.querySelector(".active")?.scrollIntoView?.({ inline: "nearest", block: "nearest" });
  }, [pathname]);

  function pendingCount(step: Step): number {
    if (!step.kind || !resolution) return 0;
    const kinds = step.kind;
    return resolution.choices.filter(
      (c) => kinds.includes(c.source.kind) && (!step.cidFilter || step.cidFilter(c.id)) && c.status === "pending"
    ).length;
  }

  return (
    <nav className="step-nav" ref={navRef}>
      {STEPS.map((step) => {
        const count = pendingCount(step);
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
