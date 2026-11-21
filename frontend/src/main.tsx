import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { engineSnapshot, startEngine, subscribeEngine, transport } from "./api/transport";
import { whenEngineSettled } from "./api/whenEngineSettled";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { DraftProvider } from "./DraftContext";
import { LanguageProvider } from "./LanguageContext";
import { LibraryProvider } from "./LibraryContext";
import "./index.css";
import "./print.css";
import { startPwa } from "./pwa/pwaStore";

// Start the in-browser engine (if this build uses it) while the first screen is drawn.
startEngine();
// The service worker (offline use) only where the in-browser engine is in use; the Flask build and the dev server never get one.
// It starts once the engine has booted (or after 45 s): the 20 MB precache would otherwise compete with the engine's own files.
void transport().chosen.then(async (choice) => {
  if (choice !== "worker") return;
  await whenEngineSettled(engineSnapshot, subscribeEngine, 45_000);
  startPwa();
});

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("#root element not found");

createRoot(rootElement).render(
  <StrictMode>
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <LanguageProvider>
        <ErrorBoundary>
          <LibraryProvider>
            <DraftProvider>
              <App />
            </DraftProvider>
          </LibraryProvider>
        </ErrorBoundary>
      </LanguageProvider>
    </BrowserRouter>
  </StrictMode>,
);
