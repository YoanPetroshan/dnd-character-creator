import { Routes, Route, Navigate, NavLink, useLocation } from "react-router-dom";
import { CatalogProvider } from "./CatalogContext";
import { ResolutionProvider } from "./ResolutionContext";
import { LanguageSwitch } from "./components/LanguageSwitch";
import { StepNav } from "./components/StepNav";
import { NextStepLink } from "./components/NextStepLink";
import { NextStepButton } from "./components/NextStepButton";
import { NewChoicesLink } from "./components/NewChoicesLink";
import { NewChoicesProvider } from "./NewChoicesContext";
import { StatusBanner } from "./components/StatusBanner";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { RouteA11y } from "./components/RouteA11y";
import { exportRedirectTarget } from "./logic/exportRedirect";
import { HomePage } from "./pages/HomePage";
import { ClassPage } from "./pages/ClassPage";
import { BackgroundPage } from "./pages/BackgroundPage";
import { SpeciesPage } from "./pages/SpeciesPage";
import { AbilitiesPage } from "./pages/AbilitiesPage";
import { EquipmentPage } from "./pages/EquipmentPage";
import { SheetPage } from "./pages/SheetPage";
import { HelpPage } from "./pages/HelpPage";
import { useT } from "./LanguageContext";

/** The old Export page is the Sheet page now; the query string (e.g. ?tab) is kept. */
function ExportRedirect() {
  const { search } = useLocation();
  return <Navigate to={exportRedirectTarget(search)} replace />;
}

export default function App() {
  const location = useLocation();
  const t = useT();
  return (
    <div className="app">
      <CatalogProvider>
        <ResolutionProvider>
          <NewChoicesProvider>
          <RouteA11y />
          <header className="app-header">
            <NavLink className="help-link" to="/help">
              {t.nav.help}
            </NavLink>
            <LanguageSwitch />
          </header>
          <StepNav />
          <NextStepLink />
          <NewChoicesLink />
          <StatusBanner />
          <main>
            {/* per-route boundary: a crash on one page keeps the nav usable, and navigating away clears it */}
            <ErrorBoundary key={location.pathname}>
            <Routes>
              <Route path="/" element={<Navigate to="/home" replace />} />
              <Route path="/home" element={<HomePage />} />
              <Route path="/class" element={<ClassPage />} />
              <Route path="/background" element={<BackgroundPage />} />
              <Route path="/species" element={<SpeciesPage />} />
              <Route path="/abilities" element={<AbilitiesPage />} />
              <Route path="/equipment" element={<EquipmentPage />} />
              <Route path="/sheet" element={<SheetPage />} />
              <Route path="/export" element={<ExportRedirect />} />
              <Route path="/help" element={<HelpPage />} />
              <Route path="*" element={<Navigate to="/home" replace />} />
            </Routes>
            </ErrorBoundary>
            <NextStepButton />
          </main>
          </NewChoicesProvider>
        </ResolutionProvider>
      </CatalogProvider>
    </div>
  );
}
