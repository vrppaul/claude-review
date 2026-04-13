import type { DiffFile } from "$lib/types";

/**
 * Languages that support rendered preview (Preview / Side-by-side modes).
 * To add a new renderable format: add it here, then provide a renderer component.
 * Currently: markdown → MarkdownRenderer.svelte
 */
const RENDERABLE_LANGUAGES = new Set(["markdown"]);

export function isRenderable(language: string | null): boolean {
  return language !== null && RENDERABLE_LANGUAGES.has(language);
}

/** Assemble displayable text from a file's hunks, skipping deleted lines in diff mode. */
export function assembleText(file: DiffFile, isDiffMode: boolean): string {
  return file.hunks
    .flatMap((h) => h.lines)
    .filter((line) => !isDiffMode || line.type !== "delete")
    .map((l) => l.content)
    .join("\n");
}
