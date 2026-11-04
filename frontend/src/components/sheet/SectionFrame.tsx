import type { ReactNode } from "react";

/** The frame every sheet section renders in: a labelled <section> that carries its key for tests and print hooks. */
export function SectionFrame({ sectionKey, title, children }: { sectionKey: string; title: string; children: ReactNode }) {
  const id = `sheet-${sectionKey}`;
  return (
    <section data-section={sectionKey} aria-labelledby={id}>
      <h2 id={id}>{title}</h2>
      {children}
    </section>
  );
}
