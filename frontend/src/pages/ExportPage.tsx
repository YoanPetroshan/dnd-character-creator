import { useState } from "react";
import { Link } from "react-router-dom";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { httpErrorMessage } from "../httpErrors";
import { exportReadiness } from "../logic/exportReadiness";
import { stepForChoice } from "../logic/steps";
import { safeFilename, shareOrDownload } from "../logic/files";
import { ClassResourcesList } from "../components/ClassResourcesList";
import { SheetTraitsSummary } from "../components/SheetTraitsSummary";
import { SpellSlotsSummary } from "../components/SpellSlotsSummary";

const EXPORT_FORMATS = {
  yaml: { endpoint: "/api/export/yaml", extension: "yaml", label: "YAML" },
  markdown: { endpoint: "/api/export/markdown", extension: "md", label: "Markdown" },
  pdf: { endpoint: "/api/export/pdf", extension: "pdf", label: "PDF" },
} as const;

type ExportFormat = keyof typeof EXPORT_FORMATS;

export function ExportPage() {
  const { draft } = useDraft();
  const { resolution, loading, error } = useResolutionContext();
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = useState<ExportFormat | null>(null);

  if (!resolution) return <div className="page">{error ? null : "Зареждане…"}</div>;

  // Mirrors server/app.py `_pending_export_problems` (see logic/exportReadiness.ts).
  const { missingParts, pendingChoices, pendingEquipment, canExport } = exportReadiness(resolution, error);

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
        const problemText = body.problems?.map((p) => p.message).join("; ");
        if (problemText) throw new Error(`Експортът е отказан, докато има проблеми в черновата: ${problemText}`);
        throw new Error(`Експортът не успя. ${httpErrorMessage(resp.status, body.error ?? "")}`);
      }
      const blob = await resp.blob();
      await shareOrDownload(blob, safeFilename(draft.name, config.extension));
    } catch (err) {
      setExportError(
        err instanceof TypeError ? "Няма връзка със сървъра. Експортът не е изтеглен." : err instanceof Error ? err.message : String(err),
      );
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
              <li key={c.id}>
                <Link to={{ pathname: stepForChoice(c.id), hash: c.id }}>{c.label}</Link>
              </li>
            ))}
          </ul>
        </div>
      )}
      <SheetTraitsSummary sheet={resolution.sheet} />
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
                {a.mastery && `, mastery ${a.mastery}`}
              </li>
            ))}
          </ul>
        </div>
      )}
      {(resolution.sheet.weaponMasteries?.length ?? 0) > 0 && (
        <div>
          <h2>Майсторство с оръжия</h2>
          <ul>
            {resolution.sheet.weaponMasteries!.map((m) => (
              <li key={m.itemId}>
                {m.name}: {m.mastery}
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
      {(resolution.derived.featResources?.length ?? 0) > 0 && (
        <div>
          <h2>Ресурси от таланти</h2>
          <ClassResourcesList resources={resolution.derived.featResources!} />
        </div>
      )}
      {(resolution.derived.speciesResources?.length ?? 0) > 0 && (
        <div>
          <h2>Ресурси от расата</h2>
          <ClassResourcesList resources={resolution.derived.speciesResources!} />
        </div>
      )}
      {(resolution.sheet.feats?.length ?? 0) > 0 && (
        <div>
          <h2>Таланти</h2>
          <ul>
            {resolution.sheet.feats!.map((f, i) => (
              // a repeatable feat (Elemental Adept, Magic Initiate, Skilled) appears once per pick with the same id
              <li key={`${f.id}:${f.origin}:${f.level ?? ""}:${i}`}>
                {f.name}
                {f.choice && f.choice.length > 0 && `: ${f.choice.join(", ")}`}
                {f.notes && f.notes.length > 0 && ` — ${f.notes.join("; ")}`}
              </li>
            ))}
          </ul>
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
      {exportError && <p role="alert" style={{ color: "red" }}>{exportError}</p>}
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
