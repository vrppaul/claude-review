/**
 * The choices a reader makes about how a review is drawn.
 *
 * Which layout, whether whitespace counts, how a markdown file is shown:
 * none of these belong to a particular review, they are how this person
 * reads. Kept beside the theme, in the browser's own storage, and read back
 * before the first paint of the diff.
 */

function key(name: string): string {
  return `claude-review:${name}`;
}

/** Read a stored choice, falling back when it is missing or no longer valid. */
export function readChoice<T extends string>(
  name: string,
  allowed: readonly T[],
  fallback: T,
): T {
  try {
    const stored = localStorage.getItem(key(name));
    return allowed.includes(stored as T) ? (stored as T) : fallback;
  } catch {
    // Private mode and blocked site data both throw; the default is fine
    return fallback;
  }
}

export function readFlag(name: string, fallback = false): boolean {
  try {
    const stored = localStorage.getItem(key(name));
    return stored === null ? fallback : stored === "on";
  } catch {
    return fallback;
  }
}

/**
 * Read a stored measurement, holding it to what the layout can take.
 *
 * A width saved on a wide screen must not leave a narrow one with no room
 * for the diff, so the bounds are applied on the way out rather than only
 * when it is set.
 */
export function readNumber(
  name: string,
  { min, max, fallback }: { min: number; max: number; fallback: number },
): number {
  try {
    const stored = Number.parseInt(localStorage.getItem(key(name)) ?? "", 10);
    if (!Number.isFinite(stored)) return fallback;
    return Math.min(max, Math.max(min, stored));
  } catch {
    return fallback;
  }
}

export function writeChoice(
  name: string,
  value: string | number | boolean,
): void {
  try {
    const stored =
      typeof value === "boolean" ? (value ? "on" : "off") : String(value);
    localStorage.setItem(key(name), stored);
  } catch {
    // The choice still applies to this tab, it just will not be remembered
  }
}
