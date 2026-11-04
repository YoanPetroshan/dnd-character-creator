import { Component, type ErrorInfo, type ReactNode } from "react";

import { useT } from "../LanguageContext";
import { activeDraftRaw, browserStorage, resetActiveDraft } from "../library";

interface State {
  error: Error | null;
}

/** Top-level safety net: a render crash (e.g. a corrupt stored draft) must
 *  not leave a white page that persists across reloads. Offers to save the
 *  raw stored draft of the active character to a file and to reset it. Reads localStorage directly,
 *  since it sits above the providers. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("UI crashed", error, info.componentStack);
  }

  private download = () => {
    let raw = "{}";
    try {
      raw = activeDraftRaw(browserStorage()) ?? "{}";
    } catch {
      // storage unavailable — export an empty object
    }
    const url = URL.createObjectURL(new Blob([raw], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "character-draft-backup.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  private retry = () => this.setState({ error: null });

  private reset = () => {
    try {
      resetActiveDraft(browserStorage()); // only the active character; the others stay
    } catch {
      // ignore
    }
    window.location.assign("/home");
  };

  render() {
    if (!this.state.error) return this.props.children;
    return <ErrorView message={this.state.error.message} onRetry={this.retry} onDownload={this.download} onReset={this.reset} />;
  }
}

/** The fallback page. A function component so it can read the language; the boundary itself cannot. */
function ErrorView({ message, onRetry, onDownload, onReset }: { message: string; onRetry: () => void; onDownload: () => void; onReset: () => void }) {
  const t = useT();
  return (
    <div className="page" role="alert">
      <h1>{t.errorBoundary.title}</h1>
      <p>{t.errorBoundary.body(message)}</p>
      <p>{t.errorBoundary.hint}</p>
      <button type="button" onClick={onRetry}>
        {t.common.retry}
      </button>{" "}
      <button type="button" onClick={onDownload}>
        {t.errorBoundary.download}
      </button>{" "}
      <button type="button" onClick={onReset}>
        {t.errorBoundary.reset}
      </button>
    </div>
  );
}
