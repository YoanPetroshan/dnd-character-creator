// Minimal typings for the few Node APIs the test files use (the project has no @types/node).
declare const process: { env: Record<string, string | undefined> };
declare const Buffer: {
  from(data: string | Uint8Array, encoding?: string): Uint8Array & { toString(encoding?: string): string };
};
declare module "node:fs" {
  export function existsSync(path: URL | string): boolean;
  export function readFileSync(path: URL | string): Uint8Array & { toString(encoding?: string): string };
  export function writeFileSync(path: URL | string, data: Uint8Array | string): void;
  export function mkdirSync(path: URL | string, options?: { recursive?: boolean }): void;
  export function readdirSync(path: URL | string): string[];
  export function statSync(path: URL | string): { isDirectory(): boolean };
}
declare module "node:zlib" {
  export function gzipSync(data: Uint8Array, options?: { level?: number }): Uint8Array;
  export function gunzipSync(data: Uint8Array): Uint8Array & { toString(encoding?: string): string };
}
