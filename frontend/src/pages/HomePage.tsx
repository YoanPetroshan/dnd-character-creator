import { useDraft } from "../DraftContext";
import { useLibrary } from "../LibraryContext";
import { useLang, useT } from "../LanguageContext";
import { randomName } from "../logic/randomName";
import { HeroPortrait } from "../components/HeroPortrait";
import { HeroDetailsForm } from "../components/HeroDetailsForm";

/** The Hero step (first step): portrait, name and the hero's description (DESIGN-L, decision 3A). The hero library is
 *  /heroes, the set-once options are /settings. */
export function HomePage() {
  const t = useT();
  const { lang } = useLang();
  const { draft, dispatch } = useDraft();
  const library = useLibrary();
  return (
    <div className="page" data-page="home">
      <h1>{t.home.title}</h1>
      <div className="home-side">
      <div className="home-portrait">
        <HeroPortrait id={library.activeId} classId={draft.classes[0]?.classId} />
      </div>
      <div className="name-row">
        <label className="name-row__field">
          <span className="name-row__label">{t.home.nameLabel}</span>
          <input
            type="text"
            value={draft.name}
            onChange={(e) => dispatch({ type: "SET_NAME", name: e.target.value })}
          />
        </label>
        <button
          type="button"
          className="name-dice"
          aria-label={t.home.randomName}
          onClick={() => dispatch({ type: "SET_NAME", name: randomName(lang, Math.random) })}
        >
          {t.home.randomNameIcon}
        </button>
      </div>
      </div>
      <div className="home-main">
        <HeroDetailsForm />
      </div>
    </div>
  );
}
