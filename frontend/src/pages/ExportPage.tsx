import { useState } from "react";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { ClassResourcesList } from "../components/ClassResourcesList";
import { SpellSlotsSummary } from "../components/SpellSlotsSummary";

const EXPORT_FORMATS = {
  yaml: { endpoint: "/api/export/yaml", extension: "yaml", label: "YAML" },
  markdown: { endpoint: "/api/export/markdown", extension: "md", label: "Markdown" },
  pdf: { endpoint: "/api/export/pdf", extension: "pdf", label: "PDF" },
} as const;

type ExportFormat = keyof typeof EXPORT_FORMATS;

export function ExportPage() {
  const { draft, dispatch } = useDraft();
  const resetDraft = () => {
    if (window.confirm("Нулиране на черновата? Текущият герой ще бъде изтрит.")) dispatch({ type: "RESET" });
  };
  const { resolution, loading, error, retry } = useResolutionContext();
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = useState<ExportFormat | null>(null);

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>{" "}
        <button type="button" onClick={resetDraft}>
          Нулирай чернова
        </button>
      </div>
    );
  if (!resolution) return <div className="page">Зареждане…</div>;

  // Must mirror server/app.py `_pending_export_problems`: equipment choices
  // never block export.
  const allPending = resolution.choices.filter((c) => c.status === "pending");
  const pendingChoices = allPending.filter((c) => c.source.kind !== "equipment");
  const pendingEquipment = allPending.filter((c) => c.source.kind === "equipment");
  // Also mirrors the server gate: a character needs a class, species and background.
  const missingParts = [
    resolution.sheet.classes.length === 0 && "Избери клас.",
    !resolution.sheet.species && "Избери species.",
    !resolution.sheet.background && "Избери background.",
  ].filter((m): m is string => typeof m === "string");
  const canExport = resolution.problems.length === 0 && pendingChoices.length === 0 && missingParts.length === 0;

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
        let body: { problems?: { message: string }[]; error?: string } = {};
        try {
          body = await resp.json();
        } catch {
          // non-JSON error body
        }
        throw new Error(
          body.problems?.map((p) => p.message).join("; ") ?? body.error ?? `export failed: ${resp.status}`
        );
      }
      const blob = await resp.blob();
      const filename = `${(draft.name || "character").replace(/[\\/:*?"<>|]/g, "_")}.${config.extension}`;

      // Touch devices: prefer the native share sheet (iOS Safari often
      // ignores a.download for PDF/text and would navigate away instead).
      if (typeof File !== "undefined" && navigator.canShare && window.matchMedia("(pointer: coarse)").matches) {
        const file = new File([blob], filename, { type: blob.type });
        if (navigator.canShare({ files: [file] })) {
          try {
            await navigator.share({ files: [file] });
            return;
          } catch (shareErr) {
            if (shareErr instanceof DOMException && shareErr.name === "AbortError") return;
            // Any other share failure: fall through to the download link.
          }
        }
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      a.remove();
      // Revoking immediately can cancel the download in iOS/Android WebViews.
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
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
      {missingParts.length > 0 && (
        <ul role="alert">
          {missingParts.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
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
      {((resolution.derived.attacks?.length ?? 0) > 0 || (resolution.derived.attacksPerAction ?? 1) > 1) && (
        <div>
          <h2>Attacks</h2>
          <ul>
            <li>Attacks per action: {resolution.derived.attacksPerAction ?? 1}</li>
            {(resolution.derived.attacks ?? []).map((a) => (
              <li key={a.itemId}>
                {a.name}: {a.attackBonus >= 0 ? "+" : ""}
                {a.attackBonus}
                {a.damage && `, ${a.damage} ${a.damageType}`}
                {a.versatileDamage && ` (versatile ${a.versatileDamage})`}
                {a.duelingDamage && `, with Dueling ${a.duelingDamage}`}
                {a.offhandDamage && `, off hand ${a.offhandDamage}`}
                {a.range && `, range ${a.range}`}
                {a.notes.length > 0 && `; ${a.notes.join(", ")}`}
              </li>
            ))}
          </ul>
        </div>
      )}
      {(resolution.derived.classResources?.length ?? 0) > 0 && (
        <div>
          <h2>Ресурси на класа</h2>
          <ClassResourcesList resources={resolution.derived.classResources!} />
        </div>
      )}
      <SpellSlotsSummary resolution={resolution} />
      {resolution.derived.carryingCapacity && (
        <p>
          Carrying: {resolution.derived.carryingCapacity.carried}/{resolution.derived.carryingCapacity.capacity} lb
          (push/drag/lift {resolution.derived.carryingCapacity.pushDragLift} lb)
          {resolution.derived.carryingCapacity.overCapacity && " - over capacity"}
          {resolution.derived.stealthDisadvantage && "; armor: disadvantage on Stealth"}
        </p>
      )}
      {pendingEquipment.length > 0 && (
        <p>Не всички избори за екипировка са направени ({pendingEquipment.length}) — това не блокира експорта.</p>
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
