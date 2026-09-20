import { Routes, Route, Navigate } from "react-router-dom";
import { CatalogProvider } from "./CatalogContext";
import { ResolutionProvider } from "./ResolutionContext";
import { StepNav } from "./components/StepNav";
import { HomePage } from "./pages/HomePage";
import { ClassPage } from "./pages/ClassPage";
import { BackgroundPage } from "./pages/BackgroundPage";
import { SpeciesPage } from "./pages/SpeciesPage";
import { AbilitiesPage } from "./pages/AbilitiesPage";
import { EquipmentPage } from "./pages/EquipmentPage";
import { ExportPage } from "./pages/ExportPage";

export default function App() {
  return (
    <div className="app">
      <CatalogProvider>
        <ResolutionProvider>
          <StepNav />
          <main>
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
          </main>
        </ResolutionProvider>
      </CatalogProvider>
    </div>
  );
}
