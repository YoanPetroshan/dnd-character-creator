import { useSearchParams } from "react-router-dom";
import { ExportBar } from "../components/sheetpage/ExportBar";
import { CombatRow, SheetHero, SummaryStrip } from "../components/sheetpage/SummaryStrip";
import { SheetEyesProvider } from "../components/sheet/SheetEyes";
import { Tabs, type TabDef } from "../components/sheetpage/Tabs";
import { ActionsPanel, BackgroundPanel, FeaturesPanel, InventoryPanel, NotesPanel, ReferenceBlock, SpellsPanel } from "../components/sheetpage/panels";
import { useDraft } from "../DraftContext";
import { useT } from "../LanguageContext";
import { exportReadiness } from "../logic/exportReadiness";
import { sheetSections } from "../logic/sheetSections";
import { TAB_IDS, parseTab, type TabId } from "../logic/sheetTabs";
import { useResolutionContext } from "../ResolutionContext";

/** The character sheet page (/sheet, also the old /export): the download buttons at the top, a summary strip, then tabs
 *  (`?tab=actions|spells|inventory|features|background|notes`, default actions). The layout follows the familiar online
 *  sheet: header with the picture, a row of number boxes, then saves / senses / proficiencies, skills and the tab panel in
 *  three columns on a wide screen. Works on an unfinished draft too: the
 *  downloads are then disabled and the page says why. */
export function SheetPage() {
  const t = useT();
  const { draft } = useDraft();
  const { resolution, loading, error } = useResolutionContext();
  const [params, setParams] = useSearchParams();
  const tab = parseTab(params.get("tab"));

  if (!resolution) {
    return (
      <div className="page" data-page="sheet">
        <h1>{t.sheet.title}</h1>
        {!error && <p>{t.sheet.loading}</p>}
      </div>
    );
  }

  const { missingParts, pendingChoices, problems } = exportReadiness(resolution, error);
  const outstanding = missingParts.length + pendingChoices.length + problems.length;
  const sections = sheetSections(resolution, draft.abilities.base);
  const tabs: TabDef<TabId>[] = TAB_IDS.map((id) => ({ id, label: t.sheet.tabs[id] }));

  function select(id: TabId) {
    const next = new URLSearchParams(params);
    next.set("tab", id);
    setParams(next, { replace: true });
  }

  return (
    <div className="page" data-page="sheet" data-tab={tab}>
      <h1>
        {t.sheet.title} {loading && "…"}
      </h1>
      <SheetHero sections={sections} />
      <ExportBar resolution={resolution} error={error} />
      {outstanding > 0 && (
        <p role="status" data-state="incomplete">
          {t.sheet.incomplete(outstanding)}
        </p>
      )}
      <SummaryStrip sections={sections} />
      <div className="sheet-body">
      <div className="sheet-main">
      <CombatRow sections={sections} />
      <SheetEyesProvider>
      <Tabs
        idPrefix="sheet"
        label={t.sheet.tabs.label}
        tabs={tabs}
        selected={tab}
        onSelect={select}
        renderPanel={(id) => {
          switch (id) {
            case "actions":
              return <ActionsPanel sections={sections} />;
            case "spells":
              return <SpellsPanel sections={sections} resolution={resolution} />;
            case "inventory":
              return <InventoryPanel sections={sections} />;
            case "features":
              return <FeaturesPanel resolution={resolution} />;
            case "background":
              return <BackgroundPanel sections={sections} />;
            case "notes":
              return <NotesPanel sections={sections} />;
          }
        }}
      />
      </SheetEyesProvider>
      </div>
      <ReferenceBlock sections={sections} />
      </div>
    </div>
  );
}
