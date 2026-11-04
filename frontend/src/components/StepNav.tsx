import { useEffect, useRef } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { STEPS, stepBadgeCount, stepStatus } from "../logic/steps";

export function StepNav() {
  const { draft } = useDraft();
  const { resolution } = useResolutionContext();
  const navRef = useRef<HTMLElement>(null);
  const { pathname } = useLocation();

  // Keep the active step visible when the nav scrolls horizontally on phones.
  useEffect(() => {
    navRef.current?.querySelector(".active")?.scrollIntoView?.({ inline: "nearest", block: "nearest" });
  }, [pathname]);

  const status = stepStatus(resolution, draft);

  return (
    <nav className="step-nav" aria-label="Стъпки" ref={navRef}>
      {STEPS.map((step) => {
        const count = stepBadgeCount(status[step.path]);
        return (
          <NavLink key={step.path} to={step.path} className={({ isActive }) => (isActive ? "active" : "")}>
            {step.label}
            {count > 0 && (
              <span className="step-nav__badge" role="img" aria-label={`неизбрани: ${count}`}>
                {count}
              </span>
            )}
          </NavLink>
        );
      })}
    </nav>
  );
}
