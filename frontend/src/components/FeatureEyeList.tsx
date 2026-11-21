import type { ReactNode } from "react";
import { useT } from "../LanguageContext";
import type { SheetFeat, SheetFeature } from "../types";
import { featureEyeTarget, useSheetEyes } from "./sheet/SheetEyes";

/** One feature as a card: the title line (name, level or a note, what the player picked) opens its text. A feature with no
 *  text behind it is a plain line. Needs a SheetEyesProvider above it (the Class, Species and Background pages wrap themselves). */
export function FeatureCard({ rowKey, feature, meta }: { rowKey: string; feature: SheetFeature; meta?: ReactNode }) {
  const eyes = useSheetEyes();
  const target = featureEyeTarget(feature.ref);
  const open = !!(eyes && target && eyes.isOpen(rowKey));
  const head = (
    <>
      <span className="feature-card__title">{feature.name}</span>
      {meta ? <span className="feature-card__meta">{meta}</span> : null}
      {feature.choice && feature.choice.length > 0 && <span className="feature-card__picked">{feature.choice.join(", ")}</span>}
    </>
  );
  return (
    <li className="feature-card" data-open={open ? "true" : undefined}>
      {eyes && target ? (
        <button type="button" className="feature-card__head" aria-expanded={open} onClick={() => eyes.toggle(rowKey, target.kind, target.id)}>
          {head}
        </button>
      ) : (
        <div className="feature-card__head feature-card__head--plain">{head}</div>
      )}
      {open && eyes && target && <div className="feature-card__body">{eyes.body(target.kind, target.id, true)}</div>}
    </li>
  );
}

/** A plain list of features (species traits, the background's feature and feat). */
export function FeatureEyeList({ idPrefix, features }: { idPrefix: string; features: SheetFeature[] }) {
  if (features.length === 0) return null;
  return (
    <ul className="feature-cards">
      {features.map((f, i) => (
        <FeatureCard key={`${f.name}:${i}`} rowKey={`${idPrefix}:${i}`} feature={f} />
      ))}
    </ul>
  );
}

/** A row that is not a feature of the class list (the Ability Score Improvement of a level, the subclass pick). */
export interface ExtraRow {
  level: number;
  key: string;
  name: string;
  choice?: string[];
}

/** One class's features as cards in level order, each with its level; `extra` rows are placed by level. */
export function LevelFeatureList({ idPrefix, features, extra }: { idPrefix: string; features: SheetFeature[]; extra: ExtraRow[] }) {
  const t = useT();
  const rows: { level: number; order: number; node: ReactNode }[] = [];
  features.forEach((f, i) =>
    rows.push({
      level: f.level ?? 1,
      order: i,
      node: <FeatureCard key={`f:${f.name}:${i}`} rowKey={`${idPrefix}:${i}`} feature={f} meta={t.classPage.levelN(f.level ?? 1)} />,
    }),
  );
  extra.forEach((e, i) =>
    rows.push({
      level: e.level,
      order: 1000 + i,
      node: (
        <FeatureCard
          key={`x:${e.key}`}
          rowKey={`${idPrefix}:x:${e.key}`}
          feature={{ source: { kind: "class", id: "", label: "" }, name: e.name, level: e.level, ...(e.choice?.length ? { choice: e.choice } : {}) }}
          meta={t.classPage.levelN(e.level)}
        />
      ),
    }),
  );
  rows.sort((a, b) => a.level - b.level || a.order - b.order);
  if (rows.length === 0) return null;
  return <ul className="feature-cards">{rows.map((r) => r.node)}</ul>;
}

/** The features a species or a background gives, for the list under its picker: its traits / feature (`kind`) and the origin
 *  feat it grants (a feat row of the sheet with that origin), each as a card that opens its text. */
export function grantedFeatures(
  sheet: { features?: SheetFeature[]; feats?: SheetFeat[] } | undefined,
  kind: "species" | "background",
): SheetFeature[] {
  const own = (sheet?.features ?? []).filter((f) => f.source.kind === kind);
  const feats = (sheet?.feats ?? [])
    .filter((f) => f.origin === kind)
    .map((f): SheetFeature => ({ source: { kind: "feat", id: f.id, label: f.name }, name: f.name, level: null, ref: { kind: "feat", id: f.id }, ...(f.choice?.length ? { choice: f.choice } : {}) }));
  return [...own, ...feats];
}
