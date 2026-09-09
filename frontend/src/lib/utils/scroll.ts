/**
 * Where each file sits in the stream.
 *
 * The sidebar and the comment navigator move the reader by scrolling rather
 * than by swapping what is rendered, so find-in-page, text selection across
 * files and the browser's own history all keep working. Sections announce
 * themselves here instead of being looked up by selector, which keeps path
 * characters out of a query string.
 */
const sections = new Map<string, HTMLElement>();

export function registerSection(
  path: string,
  element: HTMLElement,
): () => void {
  sections.set(path, element);
  return () => {
    if (sections.get(path) === element) sections.delete(path);
  };
}

export function scrollToFile(path: string): void {
  sections.get(path)?.scrollIntoView({ block: "start" });
}

export function scrollToComment(commentId: string): void {
  document
    .getElementById(commentId)
    ?.scrollIntoView({ behavior: "smooth", block: "center" });
}

/**
 * Report which files are inside a thin band across the top of the reading
 * area, so the sidebar can follow the scroll instead of driving it.
 *
 * The band, rather than the whole viewport, is what makes "current" mean the
 * file whose header is pinned at the top: a long file below it is visible
 * too, but it is not the one being read.
 */
export function observeFilesInView(
  container: HTMLElement,
  onChange: (visiblePaths: ReadonlySet<string>) => void,
): () => void {
  const visible = new Set<string>();

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        const path = (entry.target as HTMLElement).dataset.path;
        if (!path) continue;
        if (entry.isIntersecting) visible.add(path);
        else visible.delete(path);
      }
      onChange(visible);
    },
    { root: container, rootMargin: "0px 0px -85% 0px", threshold: 0 },
  );

  for (const section of container.querySelectorAll(
    '[data-testid="file-section"]',
  )) {
    observer.observe(section);
  }
  return () => observer.disconnect();
}
