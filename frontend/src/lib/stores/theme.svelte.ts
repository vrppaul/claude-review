import type { Theme } from "$lib/types";
import { settingsStore } from "$lib/stores/settings.svelte";

export type ResolvedTheme = "light" | "dark";

const SYSTEM_PREFERS_DARK = "(prefers-color-scheme: dark)";

function systemTheme(): ResolvedTheme {
  // Absent in jsdom and in browsers old enough not to matter here
  if (typeof window.matchMedia !== "function") return "dark";
  return window.matchMedia(SYSTEM_PREFERS_DARK).matches ? "dark" : "light";
}

let system = $state<ResolvedTheme>(systemTheme());

const resolved = $derived<ResolvedTheme>(
  settingsStore.settings.theme === "system"
    ? system
    : settingsStore.settings.theme,
);

function apply(): void {
  document.documentElement.setAttribute("data-theme", resolved);
}

/** The theme the reader chose, applied to the page, and the system's when that is the choice. */
export const themeStore = {
  get theme(): Theme {
    return settingsStore.settings.theme;
  },
  get resolved(): ResolvedTheme {
    return resolved;
  },

  set(next: Theme) {
    void settingsStore.change({ theme: next });
  },

  /**
   * Apply the theme whenever it changes — chosen here, read from the server,
   * or followed from the system. Returns a teardown.
   */
  start(): () => void {
    const stopApplying = $effect.root(() => {
      $effect(apply);
    });
    if (typeof window.matchMedia !== "function") return stopApplying;

    const query = window.matchMedia(SYSTEM_PREFERS_DARK);
    const onChange = (e: MediaQueryListEvent) => {
      system = e.matches ? "dark" : "light";
    };
    query.addEventListener("change", onChange);
    return () => {
      stopApplying();
      query.removeEventListener("change", onChange);
    };
  },

  /** Test seam: read the system's preference afresh. */
  reset() {
    system = systemTheme();
  },
};
