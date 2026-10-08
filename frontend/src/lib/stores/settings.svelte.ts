/**
 * How this reader reads a review, kept by the server for every review.
 *
 * Every review runs on a port of its own and the browser keeps one storage
 * per port, so a choice kept there was gone in the next repository's review.
 * The server keeps it in the reader's configuration instead.
 *
 * The theme is cached in this port's storage as well: the page applies it
 * before its first paint, long before the server could answer.
 */

import type {
  DiffLayout,
  ReaderSettings,
  SettingsChange,
  SettingsResponse,
  Theme,
} from "$lib/types";
import {
  forget,
  readChoice,
  readFlag,
  writeChoice,
} from "$lib/utils/preferences";

/** What a reader who has never chosen anything gets. */
const NEW_READER: ReaderSettings = {
  theme: "system",
  diff_layout: "unified",
  ignore_whitespace: false,
  sound_on_replies: false,
};

const THEMES: readonly Theme[] = ["system", "light", "dark"];
const LAYOUTS: readonly DiffLayout[] = ["unified", "split"];

// The names this browser kept choices under before the server kept them.
// The theme's stays: it is the cache the first paint reads, in index.html.
const THEME_CACHE = "theme";
const LAYOUT_KEPT_HERE = "layout";
const WHITESPACE_KEPT_HERE = "ignore-whitespace";
const SOUND_KEPT_HERE = "reply-sound";

let settings = $state<ReaderSettings>({
  ...NEW_READER,
  theme: readChoice(THEME_CACHE, THEMES, NEW_READER.theme),
});

/** What this browser kept before the server did, read under the old names. */
function keptInThisBrowser(): ReaderSettings {
  return {
    theme: readChoice(THEME_CACHE, THEMES, NEW_READER.theme),
    diff_layout: readChoice(LAYOUT_KEPT_HERE, LAYOUTS, NEW_READER.diff_layout),
    ignore_whitespace: readFlag(
      WHITESPACE_KEPT_HERE,
      NEW_READER.ignore_whitespace,
    ),
    sound_on_replies: readFlag(SOUND_KEPT_HERE, NEW_READER.sound_on_replies),
  };
}

function sameSettings(one: ReaderSettings, other: ReaderSettings): boolean {
  return (Object.keys(one) as (keyof ReaderSettings)[]).every(
    (name) => one[name] === other[name],
  );
}

async function keep(changes: SettingsChange): Promise<ReaderSettings> {
  const response = await fetch("/api/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  });
  if (!response.ok) {
    throw new Error(`Could not keep the settings: ${response.status}`);
  }
  return response.json();
}

export const settingsStore = {
  get settings(): ReaderSettings {
    return settings;
  },

  /**
   * Read what the reader chose, in this review or any other.
   *
   * A reader the server has nothing on may still have choices this browser
   * kept before the server did: they are handed over once, and the old
   * copies dropped, so no other port hands over its stale ones later.
   */
  async load(): Promise<void> {
    try {
      const response = await fetch("/api/settings");
      if (!response.ok) return;
      const kept: SettingsResponse = await response.json();
      const local = keptInThisBrowser();
      settings =
        kept.stored || sameSettings(local, NEW_READER)
          ? kept.settings
          : await keep(local);
      forget(LAYOUT_KEPT_HERE);
      forget(WHITESPACE_KEPT_HERE);
      forget(SOUND_KEPT_HERE);
      writeChoice(THEME_CACHE, settings.theme);
    } catch {
      // A server that cannot say leaves this tab reading as it was
    }
  },

  /** Make a choice, here at once and for every later review once the server has it. */
  async change(changes: Partial<ReaderSettings>): Promise<void> {
    settings = { ...settings, ...changes };
    writeChoice(THEME_CACHE, settings.theme);
    try {
      await keep(changes);
    } catch {
      // The choice still applies to this tab, it just will not be remembered
    }
  },

  /** Test seam: a reader who has never chosen anything. */
  clear() {
    settings = { ...NEW_READER };
  },
};
