/**
 * Which release of the review this reader has already been shown.
 *
 * A cookie rather than local storage: every review runs on a port of its
 * own, and local storage belongs to one port, so the welcome would come
 * back with every new repository. A cookie for 127.0.0.1 is shared by all
 * of them.
 */

const COOKIE_NAME = "claude-review-seen";
// Long enough that nobody is welcomed twice; a year is the most a browser keeps
const ONE_YEAR_SECONDS = 365 * 24 * 60 * 60;

// The numbered part of a Python release: 1.5.0 out of 1.5.0rc1 or 1.4.3.dev0
const RELEASE_NUMBERS = /^\d+(?:\.\d+)*/;

/** The release last seen, or null for somebody who has never opened a review. */
export function readSeenRelease(): string | null {
  const prefix = `${COOKIE_NAME}=`;
  const found = document.cookie
    .split("; ")
    .find((part) => part.startsWith(prefix));
  return found ? decodeURIComponent(found.slice(prefix.length)) : null;
}

export function writeSeenRelease(release: string): void {
  document.cookie = `${COOKIE_NAME}=${encodeURIComponent(release)}; path=/; max-age=${ONE_YEAR_SECONDS}; SameSite=Strict`;
}

/**
 * Whether one release came out after another.
 *
 * Numbers compared part by part, so 1.10 comes after 1.9. A pre-release or
 * a development build counts as the release it leads to: what is new is
 * written per release, and 1.5.0rc1 is about to be 1.5.0.
 */
export function isNewer(candidate: string, than: string): boolean {
  const left = releaseNumbers(candidate);
  const right = releaseNumbers(than);
  for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
    const difference = (left[index] ?? 0) - (right[index] ?? 0);
    if (difference !== 0) return difference > 0;
  }
  return false;
}

function releaseNumbers(release: string): number[] {
  const numbered = RELEASE_NUMBERS.exec(release)?.[0] ?? "";
  return numbered.split(".").map((part) => Number.parseInt(part, 10) || 0);
}
