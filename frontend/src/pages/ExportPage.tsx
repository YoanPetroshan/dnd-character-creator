import { useState } from "react";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";

const EXPORT_FORMATS = {
  yaml: { endpoint: "/api/export/yaml", extension: "yaml", label: "YAML" },
  markdown: { endpoint: "/api/export/markdown", extension: "md", label: "Markdown" },
  pdf: { endpoint: "/api/export/pdf", extension: "pdf", label: "PDF" },
} as const;

type ExportFormat = keyof typeof EXPORT_FORMATS;

export function ExportPage() {
  const { draft } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = useState<ExportFormat | null>(null);

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

  async function handleExport(format: ExportFormat) {
    const config = EXPORT_FORMATS[format];
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
      const blob = await resp.blob();
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
      {(Object.keys(EXPORT_FORMATS) as ExportFormat[]).map((format) => (
        <button
          key={format}
          type="button"
          disabled={!canExport || exportingFormat !== null}
          onClick={() => handleExport(format)}
        >
          {exportingFormat === format ? "Изтегляне…" : `Изтегли ${EXPORT_FORMATS[format].label}`}
        </button>
      ))}
    </div>
  );
}
