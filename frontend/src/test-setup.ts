/**
 * Global Vitest setup (wired via angular.json's test architect `setupFiles`).
 *
 * Recent Node.js versions ship an experimental native `localStorage` that is disabled unless
 * `--localstorage-file` is passed, and it takes precedence over jsdom's implementation — so
 * `globalThis.localStorage` ends up `undefined` under test even though it's always present in a
 * real browser. AuthService (core/auth/auth.service.ts) stores tokens in localStorage directly,
 * so tests need a working implementation regardless of the Node version running them.
 */
class MemoryStorage implements Storage {
  private readonly store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }

  clear(): void {
    this.store.clear();
  }

  getItem(key: string): string | null {
    return this.store.has(key) ? this.store.get(key)! : null;
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  setItem(key: string, value: string): void {
    this.store.set(key, value);
  }
}

if (typeof globalThis.localStorage === 'undefined' || typeof globalThis.localStorage.clear !== 'function') {
  Object.defineProperty(globalThis, 'localStorage', { value: new MemoryStorage(), configurable: true });
}
