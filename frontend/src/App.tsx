import { Routes, Route, Navigate } from "react-router-dom";

function StepPlaceholder({ name }: { name: string }) {
  return (
    <div className="page">
      <h1>{name}</h1>
    </div>
  );
}

export default function App() {
  return (
    <div className="app">
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/home" replace />} />
          <Route path="/home" element={<StepPlaceholder name="Home" />} />
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
