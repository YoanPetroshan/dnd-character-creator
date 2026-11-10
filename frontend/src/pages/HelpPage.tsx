import { Link } from "react-router-dom";
import { useT } from "../LanguageContext";
import { pwa, usePwa } from "../pwa/pwaStore";

/** Help and install: offline status, how to add the app to a phone's home screen, the 7-day storage warning with a
 *  link to the library export, and what to do when the engine cannot start. Plain text; no design. */
export function HelpPage() {
  const t = useT();
  const h = t.help;
  const offline = usePwa();
  const storageLine = offline.phase === "offline-ready" || offline.phase === "update-available" ? h.storage[offline.persisted] : undefined;
  return (
    <div className="page help-page">
      <h1>{h.title}</h1>

      <section data-section="offline">
        <h2>{h.offlineTitle}</h2>
        <p role="status" data-state={offline.phase}>
          {h.status[offline.phase]}
        </p>
        {offline.phase === "update-available" && (
          <p>
            <button type="button" onClick={() => pwa().applyUpdate()}>
              {h.updateNow}
            </button>
          </p>
        )}
        {storageLine && <p data-state={offline.persisted}>{storageLine}</p>}
      </section>

      <section data-section="install">
        <h2>{h.installTitle}</h2>
        <h3>{h.iosTitle}</h3>
        <ol>
          {h.iosSteps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
        <h3>{h.androidTitle}</h3>
        <ol>
          {h.androidSteps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
        <h3>{h.desktopTitle}</h3>
        <p>{h.desktopText}</p>
      </section>

      <section data-section="keep">
        <h2>{h.keepTitle}</h2>
        <p>{h.keepText}</p>
        <p>
          <Link to="/home">{h.keepLink}</Link>
        </p>
      </section>

      <section data-section="troubleshooting">
        <h2>{h.lockdownTitle}</h2>
        <p>{h.lockdownText}</p>
      </section>
    </div>
  );
}
