import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { COPY, DEFAULT_LANG, LANGS, copyFor, type Copy, type Lang } from "./copy";

/** The language is a per-device preference, not part of a character. */
export const LANG_KEY = "dnd-builder-lang-v1";

export function readLang(storage?: Pick<Storage, "getItem">): Lang {
  try {
    const v = (storage ?? window.localStorage).getItem(LANG_KEY);
    return (LANGS as readonly string[]).includes(v ?? "") ? (v as Lang) : DEFAULT_LANG;
  } catch {
    return DEFAULT_LANG; // storage blocked
  }
}

interface LanguageValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: Copy;
}

// without a provider (unit tests that render a component alone) the app language is the default
const LanguageContext = createContext<LanguageValue>({ lang: DEFAULT_LANG, setLang: () => undefined, t: COPY[DEFAULT_LANG] });

/** Holds the UI language (localStorage `dnd-builder-lang-v1` = bg | en, default bg) and keeps
 *  `<html lang>` in step with it. Mounted above LibraryProvider. */
export function LanguageProvider({ children, initial }: { children: ReactNode; initial?: Lang }) {
  const [lang, setLangState] = useState<Lang>(() => initial ?? readLang());

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      window.localStorage.setItem(LANG_KEY, next);
    } catch {
      // storage blocked: the choice lasts for this session only
    }
  }, []);

  const value = useMemo<LanguageValue>(() => ({ lang, setLang, t: copyFor(lang) }), [lang, setLang]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLang(): { lang: Lang; setLang: (lang: Lang) => void } {
  const { lang, setLang } = useContext(LanguageContext);
  return { lang, setLang };
}

/** The copy catalog of the active language. */
export function useT(): Copy {
  return useContext(LanguageContext).t;
}
