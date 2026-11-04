import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { routeTitle } from "../logic/routeTitle";

/** Per-route accessibility: sets document.title and, when the path changes (not on first load, not on
 *  a hash-only change), moves focus to the page's <h1> (or <main> when the page has none yet). */
export function RouteA11y() {
  const { pathname } = useLocation();
  const previous = useRef<string | null>(null);

  useEffect(() => {
    document.title = routeTitle(pathname);
    if (previous.current !== null && previous.current !== pathname) {
      const target = document.querySelector<HTMLElement>("main h1") ?? document.querySelector<HTMLElement>("main");
      if (target) {
        if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
        target.focus({ preventScroll: true });
      }
    }
    previous.current = pathname;
  }, [pathname]);

  return null;
}
