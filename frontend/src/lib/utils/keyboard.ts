/**
 * Moving around a review from the keyboard.
 *
 * Focus is the cursor: the line numbers are buttons, so moving between them
 * is moving focus, the browser scrolls it into view, and the focus ring shows
 * where you are. That saves inventing a second notion of "current line" that
 * would have to be kept in step with the real one.
 */

export function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || target.isContentEditable;
}

function gutters(): HTMLElement[] {
  return Array.from(
    document.querySelectorAll<HTMLElement>('[data-testid="line-gutter"]'),
  );
}

/** Move focus one line down or up, starting at the top when nothing is focused. */
export function moveByLine(step: 1 | -1): void {
  const all = gutters();
  if (all.length === 0) return;

  const at = all.indexOf(document.activeElement as HTMLElement);
  const next = at === -1 ? 0 : Math.min(all.length - 1, Math.max(0, at + step));
  all[next]?.focus();
}

/** The file section the reader is in, by focus if possible and by scroll if not. */
export function currentSectionPath(): string | null {
  const focused = (document.activeElement as HTMLElement | null)?.closest?.(
    '[data-testid="file-section"]',
  );
  if (focused instanceof HTMLElement && focused.dataset.path) {
    return focused.dataset.path;
  }
  return null;
}
