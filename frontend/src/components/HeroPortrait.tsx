import { useRef, useState } from "react";
import { useT } from "../LanguageContext";
import { useLibrary } from "../LibraryContext";
import { ClassGlyph } from "./ClassGlyph";

const MAX_SIDE = 512;
const QUALITY = 0.85;

/** Read an image file and downscale it in the browser: at most 512px on the long side, a JPEG data URL (quality 0.85). */
export function downscaleImage(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      try {
        const scale = Math.min(1, MAX_SIDE / Math.max(img.naturalWidth, img.naturalHeight));
        const w = Math.max(1, Math.round(img.naturalWidth * scale));
        const h = Math.max(1, Math.round(img.naturalHeight * scale));
        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        if (!ctx) throw new Error("no canvas");
        ctx.fillStyle = "#ffffff"; // a transparent PNG becomes JPEG on white, not on black
        ctx.fillRect(0, 0, w, h);
        ctx.drawImage(img, 0, 0, w, h);
        resolve(canvas.toDataURL("image/jpeg", QUALITY));
      } catch (e) {
        reject(e);
      } finally {
        URL.revokeObjectURL(url);
      }
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("unreadable image"));
    };
    img.src = url;
  });
}

/** The hero's picture: a square frame (the picture, or the class mark as a placeholder) that opens the file picker, and a
 *  row of small actions (upload, or change and remove). Renders two siblings so the parent grid places them. The picture is
 *  kept per character in the library storage, never in the draft (the engine does not receive it). */
export function HeroPortrait({ id, classId }: { id: string; classId?: string }) {
  const t = useT();
  const c = t.portrait;
  const library = useLibrary();
  const src = library.portraits[id] ?? null;
  const input = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  async function pick(file: File | undefined) {
    if (!file) return;
    try {
      const dataUrl = await downscaleImage(file);
      setError(library.setPortrait(id, dataUrl) ? null : c.storageFull);
    } catch {
      setError(c.unreadable);
    } finally {
      if (input.current) input.current.value = "";
    }
  }

  function remove() {
    setError(library.setPortrait(id, null) ? null : c.storageFull);
  }

  return (
    <>
      <button
        type="button"
        className="portrait__frame"
        data-state={src ? "set" : "empty"}
        aria-label={src ? c.change : c.upload}
        onClick={() => input.current?.click()}
      >
        {src ? <img className="portrait__img" src={src} alt="" /> : <ClassGlyph classId={classId} />}
      </button>
      <div className="portrait__actions">
        <button type="button" className="portrait__action" onClick={() => input.current?.click()}>
          {src ? c.change : c.upload}
        </button>
        {src && (
          <button type="button" className="portrait__action" onClick={remove}>
            {c.remove}
          </button>
        )}
        <input ref={input} type="file" accept="image/*" hidden onChange={(e) => pick(e.target.files?.[0])} />
        {error && (
          <p className="portrait__error" role="status">
            {error}
          </p>
        )}
      </div>
    </>
  );
}
