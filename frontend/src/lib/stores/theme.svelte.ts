export type Theme = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

/** Shared with the inline script in index.html — keep both in step. */
export const THEME_STORAGE_KEY = "claude-review:theme";

const ORDER: Theme[] = ["system", "light", "dark"];

function systemTheme(): ResolvedTheme {
  // Absent in jsdom and in browsers old enough not to matter here
  if (typeof window.matchMedia !== "function") return "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function readStored(): Theme {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") {
      return stored;
    }
  } catch {
    // Private mode and blocked site data both throw; the default is fine
  }
  return "system";
}

function persist(theme: Theme): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // The choice still applies to this tab, it just will not be remembered
  }
}

let theme = $state<Theme>(readStored());
let system = $state<ResolvedTheme>(systemTheme());

const resolved = $derived<ResolvedTheme>(theme === "system" ? system : theme);

function apply(): void {
  document.documentElement.setAttribute("data-theme", resolved);
}

export const themeStore = {
  get theme(): Theme {
    return theme;
  },
  get resolved(): ResolvedTheme {
    return resolved;
  },

  set(next: Theme) {
    theme = next;
    persist(next);
    apply();
  },

  cycle() {
    this.set(ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length]);
  },

  /**
   * Apply the current choice and keep following the system while it is the
   * choice. Returns a teardown for the listener.
   */
  start(): () => void {
    apply();
    if (typeof window.matchMedia !== "function") return () => {};

    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (e: MediaQueryListEvent) => {
      system = e.matches ? "dark" : "light";
      apply();
    };
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  },

  /** Test seam: restore the state a fresh page load would have. */
  reset() {
    theme = readStored();
    system = systemTheme();
  },
};
