import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { CatalogProvider } from "./CatalogContext";
import { ResolutionProvider } from "./ResolutionContext";
import { StepNav } from "./components/StepNav";
import { StatusBanner } from "./components/StatusBanner";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { HomePage } from "./pages/HomePage";
import { ClassPage } from "./pages/ClassPage";
import { BackgroundPage } from "./pages/BackgroundPage";
import { SpeciesPage } from "./pages/SpeciesPage";
import { AbilitiesPage } from "./pages/AbilitiesPage";
import { EquipmentPage } from "./pages/EquipmentPage";
import { ExportPage } from "./pages/ExportPage";

export default function App() {
  const location = useLocation();
  return (
    <div className="app">
      <CatalogProvider>
        <ResolutionProvider>
          <StepNav />
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
              <Route path="/export" element={<ExportPage />} />
            </Routes>
            </ErrorBoundary>
          </main>
        </ResolutionProvider>
      </CatalogProvider>
    </div>
  );
}
