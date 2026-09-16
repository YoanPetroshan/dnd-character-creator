import { Routes, Route, Navigate } from "react-router-dom";
import { useDraft } from "./DraftContext";

function StepPlaceholder({ name }: { name: string }) {
  return (
    <div className="page">
      <h1>{name}</h1>
    </div>
  );
}

function HomePlaceholder() {
  const { draft, dispatch } = useDraft();
  return (
    <div className="page">
      <h1>Home</h1>
      <label>
        Character Name
        <input
          type="text"
          value={draft.name}
          onChange={(e) => dispatch({ type: "SET_NAME", name: e.target.value })}
        />
      </label>
      <p>Saved as you type — reload the page and this name should still be here.</p>
    </div>
  );
}

export default function App() {
  return (
    <div className="app">
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/home" replace />} />
          <Route path="/home" element={<HomePlaceholder />} />
          <Route path="/class" element={<StepPlaceholder name="Class" />} />
          <Route path="/background" element={<StepPlaceholder name="Background" />} />
          <Route path="/species" element={<StepPlaceholder name="Species" />} />
          <Route path="/abilities" element={<StepPlaceholder name="Abilities" />} />
          <Route path="/equipment" element={<StepPlaceholder name="Equipment" />} />
          <Route path="/export" element={<StepPlaceholder name="Export" />} />
        </Routes>
      </main>
    </div>
  );
}
