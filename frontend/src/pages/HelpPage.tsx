import { Link } from "react-router-dom";
import { useT } from "../LanguageContext";
import { pwa, usePwa } from "../pwa/pwaStore";

/** The attribution the SRD 5.1 licence (CC-BY-4.0) asks for; the licence text is English, so it stays as it is in both languages. */
const SRD_NOTICE =
  "This work includes material taken from the System Reference Document 5.1 (\"SRD 5.1\") by Wizards of the Coast LLC and available at https://dnd.wizards.com/resources/systems-reference-document. The SRD 5.1 is licensed under the Creative Commons Attribution 4.0 International License available at https://creativecommons.org/licenses/by/4.0/legalcode.";
const ISSUES_LABEL = "GitHub";
const ISSUES_URL = "https://github.com/YoanPetroshan/dnd-character-creator/issues";

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

      <section data-section="about">
        <h2>{h.aboutTitle}</h2>
        <p>{h.aboutText}</p>
        <h3>{h.privacyTitle}</h3>
        <p>{h.privacyText}</p>
        <h3>{h.feedbackTitle}</h3>
        <p>
          {h.feedbackText} <a href={ISSUES_URL}>{ISSUES_LABEL}</a>
        </p>
        <p className="help-page__notice">{SRD_NOTICE}</p>
      </section>

      <section data-section="troubleshooting">
        <h2>{h.lockdownTitle}</h2>
        <p>{h.lockdownText}</p>
      </section>
    </div>
  );
}
