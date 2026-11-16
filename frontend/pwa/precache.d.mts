export interface FileInfo { path: string; size: number; sha256: string }
export interface PrecacheEntry { url: string; revision: string; size: number }
export interface PrecacheManifest { version: string; totalBytes: number; entries: PrecacheEntry[] }
export const DEFAULT_EXCLUDE: (path: string) => boolean;
export function sha256Hex(bytes: Uint8Array): string;
export function collectFiles(dir: string): FileInfo[];
export function buildPrecacheManifest(files: FileInfo[], exclude?: (path: string) => boolean): PrecacheManifest;
export function manifestProblems(manifest: { entries: { url: string; revision: string }[] }, files: FileInfo[], exclude?: (path: string) => boolean): { missing: string[]; stale: string[] };
export function renderServiceWorker(template: string, manifest: PrecacheManifest, schema?: number | null): string;
export function readStorageSchema(path: string | null | undefined): number | null;
export function readManifestFromServiceWorker(source: string): { version: string; schema: number | null; entries: { url: string; revision: string }[] };
export function pwaPlugin(options: { enabled: () => boolean; templatePath: string; schemaPath?: string | null; log?: (line: string) => void }): import("vite").Plugin;
