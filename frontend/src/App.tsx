import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { CatalogProvider } from "./CatalogContext";
import { ResolutionProvider } from "./ResolutionContext";
import { LanguageSwitch } from "./components/LanguageSwitch";
import { StepNav } from "./components/StepNav";
import { NextStepLink } from "./components/NextStepLink";
import { NewChoicesLink } from "./components/NewChoicesLink";
import { NewChoicesProvider } from "./NewChoicesContext";
import { StatusBanner } from "./components/StatusBanner";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { RouteA11y } from "./components/RouteA11y";
import { HomePage } from "./pages/HomePage";
import { ClassPage } from "./pages/ClassPage";
import { BackgroundPage } from "./pages/BackgroundPage";
import { SpeciesPage } from "./pages/SpeciesPage";
import { AbilitiesPage } from "./pages/AbilitiesPage";
import { EquipmentPage } from "./pages/EquipmentPage";
import { ExportPage } from "./pages/ExportPage";
import { SheetPage } from "./pages/SheetPage";

export default function App() {
  const location = useLocation();
  return (
    <div className="app">
      <CatalogProvider>
        <ResolutionProvider>
          <NewChoicesProvider>
          <RouteA11y />
          <header className="app-header">
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
              <Route path="/export" element={<ExportPage />} />
              <Route path="*" element={<Navigate to="/home" replace />} />
            </Routes>
            </ErrorBoundary>
          </main>
          </NewChoicesProvider>
        </ResolutionProvider>
      </CatalogProvider>
    </div>
  );
}
