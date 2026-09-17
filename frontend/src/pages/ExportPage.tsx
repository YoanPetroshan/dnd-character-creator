import { useState } from "react";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";

export function ExportPage() {
  const { draft } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = useState<"yaml" | "markdown" | null>(null);

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );
  if (!resolution) return <div className="page">Зареждане…</div>;

  const pendingChoices = resolution.choices.filter((c) => c.status === "pending");
  const canExport = resolution.problems.length === 0 && pendingChoices.length === 0;

  async function handleExport(format: "yaml" | "markdown") {
    const config =
      format === "yaml"
        ? { endpoint: "/api/export/yaml", extension: "yaml", mimeType: "application/x-yaml" }
        : { endpoint: "/api/export/markdown", extension: "md", mimeType: "text/markdown" };
    setExportingFormat(format);
    setExportError(null);
    try {
      const resp = await fetch(config.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
      if (!resp.ok) {
        const body = (await resp.json()) as { problems?: { message: string }[] };
        throw new Error(body.problems?.map((p) => p.message).join("; ") ?? `export failed: ${resp.status}`);
      }
      const text = await resp.text();
      const blob = new Blob([text], { type: config.mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${draft.name || "character"}.${config.extension}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : String(err));
    } finally {
      setExportingFormat(null);
    }
  }

  return (
    <div className="page">
      <h1>Export {loading && "…"}</h1>
      {resolution.problems.length > 0 && (
        <div>
          <h2>Problems</h2>
          <ul>
            {resolution.problems.map((p) => (
              <li key={p.id}>{p.message}</li>
            ))}
          </ul>
        </div>
      )}
      {pendingChoices.length > 0 && (
        <div>
          <h2>Unresolved choices</h2>
          <ul>
            {pendingChoices.map((c) => (
              <li key={c.id}>{c.label}</li>
            ))}
          </ul>
        </div>
      )}
      {canExport && <p>Всичко е готово за експорт.</p>}
      {exportError && <p style={{ color: "red" }}>{exportError}</p>}
      <button type="button" disabled={!canExport || exportingFormat !== null} onClick={() => handleExport("yaml")}>
        {exportingFormat === "yaml" ? "Изтегляне…" : "Изтегли YAML"}
      </button>
      <button type="button" disabled={!canExport || exportingFormat !== null} onClick={() => handleExport("markdown")}>
        {exportingFormat === "markdown" ? "Изтегляне…" : "Изтегли Markdown"}
      </button>
    </div>
  );
}
