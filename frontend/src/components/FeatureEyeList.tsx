import type { ReactNode } from "react";
import { useT } from "../LanguageContext";
import type { SheetFeat, SheetFeature } from "../types";
import { SheetEye, SheetEyePanel, featureEyeTarget } from "./sheet/SheetEyes";

/** One row of the list: a name, an eye (when the feature has a text behind it), what the player picked, and the open text.
 *  Needs a SheetEyesProvider above it (the Class, Species and Background pages wrap themselves in one). */
export function FeatureEyeRow({ rowKey, feature, meta }: { rowKey: string; feature: SheetFeature; meta?: ReactNode }) {
  const target = featureEyeTarget(feature.ref);
  return (
    <li className="feature">
      <strong className="feature__name">{feature.name}</strong>
      {target && <SheetEye rowKey={rowKey} kind={target.kind} id={target.id} name={feature.name} />}
      {meta ? <span className="feature__meta">{meta}</span> : null}
      {feature.choice && feature.choice.length > 0 && <span className="feature__nested">{feature.choice.join(", ")}</span>}
      {target && <SheetEyePanel rowKey={rowKey} kind={target.kind} id={target.id} />}
    </li>
  );
}

/** A plain list of features (species traits, the background's feature and feat). */
export function FeatureEyeList({ idPrefix, features }: { idPrefix: string; features: SheetFeature[] }) {
  if (features.length === 0) return null;
  return (
    <ul className="feature-list">
      {features.map((f, i) => (
        <FeatureEyeRow key={`${f.name}:${i}`} rowKey={`${idPrefix}:${i}`} feature={f} />
      ))}
    </ul>
  );
}

/** One class's features grouped under "Level N" headings, up to its current level. `extra` are rows that are not features
 *  of the class list (the Ability Score Improvement of a level, the chosen subclass), placed under their level. */
export function LevelFeatureList({
  idPrefix,
  features,
  extra,
}: {
  idPrefix: string;
  features: SheetFeature[];
  extra: { level: number; key: string; name: string; choice?: string[] }[];
}) {
  const t = useT();
  const levels = [...new Set([...features.map((f) => f.level ?? 1), ...extra.map((e) => e.level)])].sort((a, b) => a - b);
  if (levels.length === 0) return null;
  return (
    <div className="level-features">
      {levels.map((lvl) => (
        <div key={lvl} className="level-features__level" data-level={lvl}>
          <h4>{t.classPage.levelN(lvl)}</h4>
          <ul className="feature-list">
            {features
              .filter((f) => (f.level ?? 1) === lvl)
              .map((f, i) => (
                <FeatureEyeRow key={`${f.name}:${i}`} rowKey={`${idPrefix}:${lvl}:${i}`} feature={f} />
              ))}
            {extra
              .filter((e) => e.level === lvl)
              .map((e) => (
                <li key={e.key} className="feature">
                  <strong className="feature__name">{e.name}</strong>
                  {e.choice && e.choice.length > 0 && <span className="feature__nested">{e.choice.join(", ")}</span>}
                </li>
              ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

/** The features a species or a background gives, for the list under its picker: its traits / feature (`kind`) and the origin
 *  feat it grants (a feat row of the sheet with that origin), each with the eye that opens its text. */
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
