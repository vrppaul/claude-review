/**
 * Which entry of the release news a reader is shown.
 *
 * Only ever one, the newest that applies: a card that lists three releases
 * is a changelog, and the changelog is a link away.
 */

import type { ReleaseNews } from "$lib/guide/news";
import { isNewer } from "$lib/utils/seen-release";

/**
 * The newest entry a returning reader has not been shown.
 *
 * After the release they last saw and no later than the one serving them.
 * Usually that is the serving release's own entry; when it has none, the
 * newest one they skipped over speaks instead of silence.
 */
export function unseenNews(
  entries: ReleaseNews[],
  seen: string,
  serving: string,
): ReleaseNews | undefined {
  return newest(
    entries.filter(
      (entry) =>
        isNewer(entry.release, seen) && !isNewer(entry.release, serving),
    ),
  );
}

/** The newest entry up to the serving release, to read again from the ? list. */
export function latestNews(
  entries: ReleaseNews[],
  serving: string,
): ReleaseNews | undefined {
  return newest(entries.filter((entry) => !isNewer(entry.release, serving)));
}

function newest(entries: ReleaseNews[]): ReleaseNews | undefined {
  return entries.reduce<ReleaseNews | undefined>(
    (found, entry) =>
      !found || isNewer(entry.release, found.release) ? entry : found,
    undefined,
  );
}
