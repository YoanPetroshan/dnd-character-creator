import { useLang, useT } from "../LanguageContext";
import { LANGS } from "../copy";

/** Plain two-button language control: the pressed button is the active language. */
export function LanguageSwitch() {
  const t = useT();
  const { lang, setLang } = useLang();
  return (
    <div className="lang-switch" role="group" aria-label={t.lang.label}>
      {LANGS.map((code) => (
        <button key={code} type="button" lang={code} aria-pressed={lang === code} onClick={() => setLang(code)}>
          {t.lang[code]}
        </button>
      ))}
    </div>
  );
}
