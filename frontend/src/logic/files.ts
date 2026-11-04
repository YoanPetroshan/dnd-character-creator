/** A file name safe on common file systems: the user's name (or "character")
 *  with \ / : * ? " < > | replaced by "_", plus the extension. */
export function safeFilename(name: string | undefined, extension: string): string {
  return `${(name || "character").replace(/[\\/:*?"<>|]/g, "_")}.${extension}`;
}

/** Click a temporary link to download the blob. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Revoking immediately can cancel the download in iOS/Android WebViews.
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** Touch devices: prefer the native share sheet (iOS Safari often ignores
 *  a.download for PDF/text and would navigate away instead); everywhere else,
 *  or when sharing fails, download the file. `mimeType` overrides the blob's
 *  own type for the shared File (a draft is always application/json). */
export async function shareOrDownload(blob: Blob, filename: string, mimeType: string = blob.type): Promise<void> {
  if (typeof File !== "undefined" && navigator.canShare && window.matchMedia("(pointer: coarse)").matches) {
    const file = new File([blob], filename, { type: mimeType });
    if (navigator.canShare({ files: [file] })) {
      try {
        await navigator.share({ files: [file] });
        return;
      } catch (shareErr) {
        if (shareErr instanceof DOMException && shareErr.name === "AbortError") return;
        // Any other share failure: fall through to the download link.
      }
    }
  }
  downloadBlob(blob, filename);
}
