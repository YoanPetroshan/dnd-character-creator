import { Component, type ErrorInfo, type ReactNode } from "react";

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
    return (
      <div className="page" role="alert">
        <h1>Нещо се обърка</h1>
        <p>Приложението се натъкна на грешка: {this.state.error.message}</p>
        <p>Можеш да запазиш чернова като файл и да започнеш наново.</p>
        <button type="button" onClick={this.retry}>
          Опитай пак
        </button>{" "}
        <button type="button" onClick={this.download}>
          Изтегли черновата (JSON)
        </button>{" "}
        <button type="button" onClick={this.reset}>
          Нулирай черновата
        </button>
      </div>
    );
  }
}
