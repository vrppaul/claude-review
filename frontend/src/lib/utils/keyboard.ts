/**
 * Moving around a review from the keyboard.
 *
 * Focus is the cursor: the line numbers are buttons, so moving between them
 * is moving focus, the browser scrolls it into view, and the focus ring shows
 * where you are. That saves inventing a second notion of "current line" that
 * would have to be kept in step with the real one.
 */

/** Text-entry inputs; a checkbox or a button is not one of them. */
const TYPED_INTO = new Set([
  "text",
  "search",
  "email",
  "url",
  "tel",
  "password",
  "number",
]);

/**
 * Whether a key belongs to whatever has focus rather than to the review.
 *
 * Checking only the tag name caught checkboxes too, so one click on "Viewed"
 * parked focus on a hidden input and every shortcut went dead with nothing
 * on screen to explain it.
 */
export function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable || target.tagName === "TEXTAREA") return true;
  if (!(target instanceof HTMLInputElement)) return false;
  return TYPED_INTO.has(target.type);
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
