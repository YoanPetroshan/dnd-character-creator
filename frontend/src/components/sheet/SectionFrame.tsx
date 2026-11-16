import type { ReactNode } from "react";

/** The frame every sheet section renders in: a labelled <section> that carries its key for tests and print hooks.
 *  `level` 3 is for a section nested inside another one (languages inside proficiencies). */
export function SectionFrame({ sectionKey, title, level = 2, children }: { sectionKey: string; title: string; level?: 2 | 3; children: ReactNode }) {
  const id = `sheet-${sectionKey}`;
  const Heading = level === 3 ? "h3" : "h2";
  return (
    <section data-section={sectionKey} aria-labelledby={id}>
      <Heading id={id}>{title}</Heading>
      {children}
    </section>
  );
}
