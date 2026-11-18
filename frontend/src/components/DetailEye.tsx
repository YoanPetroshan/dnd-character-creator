import type { ReactNode } from "react";

/** The eye button of a row: it sits right after the name (never a sibling of a checkbox label that it could toggle). */
export function DetailEye({ label, open, onToggle }: { label: string; open: boolean; onToggle: () => void }) {
  return <button type="button" className="spell-eye" aria-label={label} aria-expanded={open} onClick={onToggle} />;
}

/** The panel an open eye shows under its row. */
export function DetailPanel({ children }: { children: ReactNode }) {
  return <div className="spell-eye__panel">{children}</div>;
}

/** Plain paragraphs of rules text (the body of an eye that carries its own text). */
export function ParagraphsBody({ paragraphs }: { paragraphs: string[] }) {
  return (
    <div className="species-eye__body">
      {paragraphs.map((paragraph, i) => (
        <p key={i} className="species-eye__lore">
          {paragraph}
        </p>
      ))}
    </div>
  );
}
