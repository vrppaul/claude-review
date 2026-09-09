/**
 * What the review says about itself from a tab strip.
 *
 * An answer can arrive while the review is in a background tab, where none
 * of the page is visible. The title carries the count and the icon takes a
 * dot — both are the browser's own furniture, and neither needs a
 * permission prompt the way a system notification would.
 */

const MARK = "#5b8def";
const OUTLINE = "#8894a6";

function icon(unread: boolean): string {
  const dot = unread ? `<circle cx="23" cy="9" r="8" fill="${MARK}"/>` : "";
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect x="3" y="7" width="26" height="19" rx="4" fill="none" stroke="${OUTLINE}" stroke-width="3"/><path d="M9 17h9" stroke="${OUTLINE}" stroke-width="3" stroke-linecap="round"/>${dot}</svg>`;
}

function iconLink(): HTMLLinkElement {
  const existing = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
  if (existing) return existing;

  const link = document.createElement("link");
  link.rel = "icon";
  document.head.appendChild(link);
  return link;
}

export function markTab(unread: number, title: string): void {
  document.title = unread > 0 ? `(${unread}) ${title}` : title;
  iconLink().href = `data:image/svg+xml,${encodeURIComponent(icon(unread > 0))}`;
}
