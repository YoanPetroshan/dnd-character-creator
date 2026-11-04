# Frontend structure (for the designer)

Everything visual lives in `frontend/src/styles/*.css`. The markup carries class names and `data-status` / `data-state` hooks; there are no inline styles. Today's look is deliberately plain; changing it is a CSS-only job.

## Stylesheets

`src/index.css` only `@import`s the files below, in this order (the order is the cascade; keep it).

| File | Contents |
| --- | --- |
| `tokens.css` | `:root` custom properties: `--font-sans`, `--space-1..5` (4/8/12/16/20 px), `--radius-sm/pill/round`, the `--color-*` greys and accents. Values equal what the app used before theming. Change the look here. |
| `base.css` | box-sizing reset, `body`, `.app` shell |
| `layout.css` | `.app-header`, `.lang-switch`, `.step-nav` (+ badge), `main`, `.page` |
| `status.css` | `.status--error` |
| `choice.css` | choice cards, pickers, pruned note |
| `abilities.css` | ability method selector, ability table, point-buy stepper |
| `lists.css` | equipment section, item browser / inventory lists, tab bar |
| `spells.css` | spell library |
| `forms.css` | details section, hit-point rolls, class blocks |
| `touch.css` | mobile/touch rules (44 px targets, 16 px inputs, safe areas, long lists). Functional: keep the minimums. |
| `hooks.css` | empty rules for classes that need no style yet (fill in as needed) |
| `print.css` | print: hides the app chrome (imported by `main.tsx`) |

Theme switch: override tokens on `:root[data-theme="..."]` (nothing sets `data-theme` yet).

## Conventions

- `data-status` = the server's status of a thing (choice `pending|resolved|unavailable`, import report entry `accepted|rejected`).
- `data-state` = the UI state of an element, one value per element:
  - choice card: `expanded | collapsed`
  - option row in a picker: `available | disabled | hidden-by-filters`
  - status banner: `error | notice | storage-failed | pruned`
  - pruned-selection list item (Home): `pruned`
  - export button: `ready | busy | disabled`; export error line: `error`
  - language button: `active | inactive`
- The step-nav link keeps the `active` class (react-router); the badge `step-nav__badge` appears only when steps are unresolved. `data-active="true"` marks the active character in the Home library list.
- Colors: `status--error` for error text. The pruned note class `choice-pruned` is defined in CSS but not rendered by any component yet.

## Component map

Presentational components take props only; logic components read contexts (`useDraft`, `useResolutionContext`, `useLang` / `useT`, `useCatalog`) and call the server.

| Area | Files | Role | Data received |
| --- | --- | --- | --- |
| Shell | `App.tsx`, `components/StepNav`, `NextStepLink`, `StatusBanner`, `LanguageSwitch`, `ErrorBoundary`, `RouteA11y` | chrome around every page | contexts only |
| Pages (logic) | `pages/HomePage, ClassPage, BackgroundPage, SpeciesPage, AbilitiesPage, EquipmentPage, SheetPage, ExportPage` | one per route, read the draft and the resolution, dispatch draft actions | draft, resolution, catalog |
| Choices | `ChoiceCard` (logic: expanded state) -> `ChoicePicker` (short and long layouts) | one server choice, selectable options | a `Choice` (id, label, status, options with `disabled`, `disabledReason`, `hiddenByFilters`, `group`, `selected`, `count`) and `onToggle` |
| Small summaries (presentational) | `ClassResourcesList`, `SheetTraitsSummary`, `SpellSlotsSummary`, `StepProblems`, `CommitNumberInput` | | resolution parts |
| Spells | `SpellLibrary` | cantrip / known / detail browser | spell lists from `useSpells` |
| Sheet (presentational) | `components/sheet/*` (`SheetView` composes the 23 sections, each in a `SectionFrame` with `data-section`) | read-only character sheet | the resolution's `sheet` / `derived` |
| Copy | `copy/bg.ts`, `copy/en.ts` | all UI text; nothing in a component is hard-coded | |

## States a designer must cover

| State | Where it shows |
| --- | --- |
| pending | choice card `data-status="pending"` (blue left border, "!" dot); step-nav badge counts |
| resolved | choice card `data-status="resolved"` |
| unavailable | choice card `data-status="unavailable"` (reason text in the body) |
| optional | a pending choice flagged optional: no "!" dot |
| disabled | picker row `data-state="disabled"` (greyed label, reason text); buttons via `:disabled` / `data-state="disabled"` |
| hidden-by-filters | picker row `data-state="hidden-by-filters"` (only shown after "show unavailable") |
| pruned | Home list of dropped selections `data-state="pruned"`; the status banner `data-state="pruned"` |
| new | not marked in the markup yet (library `seenChoiceIds` exists in data only) |
| loading / error | headings show an ellipsis while resolving; `StatusBanner` `data-state="error"` |
