import { NavLink } from "react-router-dom";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";

/** App-wide status lines shown on every page: a failed /api/resolve (the last
 *  good resolution stays on screen), a draft that could not be stored or
 *  restored, and selections the server dropped. */
export function StatusBanner() {
  const { notice, storageFailed, dismissNotice, unsavedRaw } = useDraft();
  const { resolution, error, retry } = useResolutionContext();
  const prunedCount = resolution?.pruned.length ?? 0;
  return (
    <>
      {error && (
        <p className="status-banner" role="alert">
          Грешка при изчисляване: {error}
          {resolution && " Показани са последните успешни данни."}{" "}
          <button type="button" onClick={retry}>
            Опитай пак
          </button>
        </p>
      )}
      {notice && (
        <p className="status-banner" role="status">
          {notice}{" "}
          {unsavedRaw && (
            <>
              <a href={`data:application/json;charset=utf-8,${encodeURIComponent(unsavedRaw)}`} download="dnd-draft-unreadable.json">
                Свали старата чернова
              </a>{" "}
              <button type="button" onClick={() => void navigator.clipboard?.writeText(unsavedRaw).catch(() => undefined)}>
                Копирай текста
              </button>{" "}
            </>
          )}
          <button type="button" onClick={dismissNotice}>
            Разбрах
          </button>
        </p>
      )}
      {storageFailed && (
        <p className="status-banner" role="status">
          Черновата не може да се запази в браузъра (пълно или забранено хранилище). Изтегли я от Home като файл, за да не я загубиш.
        </p>
      )}
      {prunedCount > 0 && (
        <p className="status-banner" role="status">
          Отпаднали избори: {prunedCount}. <NavLink to="/home">Виж в Home</NavLink>
        </p>
      )}
    </>
  );
}
