import { createContext, useContext, useState, type ReactNode } from "react";
import { useDraft } from "../../DraftContext";
import { useT } from "../../LanguageContext";
import type { SheetFeature } from "../../types";
import { useFeatureDetails } from "../../useFeatureDetail";
import { DetailEye, DetailPanel } from "../DetailEye";
import { FeatDetailBody, useFeatDetails } from "../FeatDetailBody";
import { FeatureDetailBody } from "../FeatureDetailBody";
import { ItemDetailBody, useItemDetails } from "../ItemDetailBody";
import { SpellDetailBody, useSpellDetails } from "../SpellDetailBody";

/** What an eye on the character sheet opens: the text of a spell, an item, a feature (class / subclass / species trait /
 *  background feature, `GET /api/features/<id>`) or a feat. */
export type EyeKind = "spell" | "item" | "feature" | "feat";

export interface Eyes {
  isOpen: (rowKey: string) => boolean;
  toggle: (rowKey: string, kind: EyeKind, id: string) => void;
  body: (kind: EyeKind, id: string, compact?: boolean) => ReactNode;
}

const EyesContext = createContext<Eyes | null>(null);

/** Holds the open eyes and the lazily fetched texts of the sheet page. Without it (SheetView, tests) the sheet has no eyes. */
export function SheetEyesProvider({ children }: { children: ReactNode }) {
  const { draft } = useDraft();
  const spells = useSpellDetails();
  const items = useItemDetails(draft.ruleset);
  const features = useFeatureDetails();
  const feats = useFeatDetails();
  const [open, setOpen] = useState<Set<string>>(new Set());
  const load = (kind: EyeKind, id: string) => {
    if (kind === "spell") spells.loadDetail(id);
    else if (kind === "item") items.loadDetail(id);
    else if (kind === "feat") feats.loadDetail(id);
    else features.loadDetail(id);
  };
  const eyes: Eyes = {
    isOpen: (rowKey) => open.has(rowKey),
    toggle: (rowKey, kind, id) => {
      if (!open.has(rowKey)) load(kind, id);
      setOpen((prev) => {
        const next = new Set(prev);
        if (next.has(rowKey)) next.delete(rowKey);
        else next.add(rowKey);
        return next;
      });
    },
    body: (kind, id, compact) => {
      if (kind === "spell") return <SpellDetailBody state={spells.details[id]} />;
      if (kind === "item") return <ItemDetailBody state={items.detailOf(id)} />;
      if (kind === "feat") return <FeatDetailBody state={feats.detailOf(id)} />;
      return <FeatureDetailBody state={features.detailOf(id)} compact={compact} />;
    },
  };
  return <EyesContext.Provider value={eyes}>{children}</EyesContext.Provider>;
}

/** The open eyes and their texts, for a list that draws its own header (the title cards of the Class, Species and Background
 *  pages). Null outside a SheetEyesProvider. */
export function useSheetEyes(): Eyes | null {
  return useContext(EyesContext);
}

/** The eye that sits right after a name; renders nothing outside the sheet page. */
export function SheetEye({ rowKey, kind, id, name }: { rowKey: string; kind: EyeKind; id: string; name: string }) {
  const t = useT();
  const eyes = useContext(EyesContext);
  if (!eyes) return null;
  const e = t.sheet.eye;
  const label = kind === "spell" ? e.spell(name) : kind === "item" ? e.item(name) : e.details(name);
  return <DetailEye label={label} open={eyes.isOpen(rowKey)} onToggle={() => eyes.toggle(rowKey, kind, id)} />;
}

/** The panel of an open eye (a block under its row; in a table use `SheetEyeRow`). */
export function SheetEyePanel({ rowKey, kind, id }: { rowKey: string; kind: EyeKind; id: string }) {
  const eyes = useContext(EyesContext);
  if (!eyes || !eyes.isOpen(rowKey)) return null;
  return <DetailPanel>{eyes.body(kind, id)}</DetailPanel>;
}

/** The panel of an open eye as a full-width table row under the row of its name. */
export function SheetEyeRow({ rowKey, kind, id, colSpan }: { rowKey: string; kind: EyeKind; id: string; colSpan: number }) {
  const eyes = useContext(EyesContext);
  if (!eyes || !eyes.isOpen(rowKey)) return null;
  return (
    <tr className="sheet-eye-row">
      <td colSpan={colSpan}>
        <DetailPanel>{eyes.body(kind, id)}</DetailPanel>
      </td>
    </tr>
  );
}

/** The eye a feature row of the sheet gets from its `ref` (feature / trait / background -> the feature text, feat -> the feat). */
export function featureEyeTarget(ref: SheetFeature["ref"]): { kind: EyeKind; id: string } | null {
  if (!ref) return null;
  if (ref.kind === "feat") return { kind: "feat", id: ref.id };
  if (ref.kind === "background") return { kind: "feature", id: `background:${ref.id}` };
  return { kind: "feature", id: ref.id };
}
