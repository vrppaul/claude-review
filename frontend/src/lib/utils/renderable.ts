import type { DiffFile, ReviewMode } from "$lib/types";

/**
 * Languages that support rendered preview (Preview / Side-by-side modes).
 * To add a new renderable format: add it here, then provide a renderer component.
 * Currently: markdown → MarkdownRenderer.svelte
 */
const RENDERABLE_LANGUAGES = new Set(["markdown"]);

export function isRenderable(language: string | null): boolean {
  return language !== null && RENDERABLE_LANGUAGES.has(language);
}

/**
 * The file's text as it reads now: in a diff the removed lines are left out,
 * since they are not in the file any more.
 */
export function assembleText(file: DiffFile, mode: ReviewMode): string {
  return file.hunks
    .flatMap((hunk) => hunk.lines)
    .filter((line) => mode !== "diff" || line.kind !== "delete")
    .map((line) => line.content)
    .join("\n");
}
