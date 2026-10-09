/**
 * Watching where files sit in the reading area: which are in the band the
 * reader reads at, and which have come near enough to be worth drawing.
 */

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

/**
 * Call back once an element comes within reach of the viewport, then stop.
 *
 * Used to decide when a file's rows are worth building. A review of sixty
 * files is tens of thousands of table rows, and building them all before
 * anything appears costs seconds — and makes every later change to the
 * comment list cost again. The margin is generous so a file is ready well
 * before it is reached, and nothing is torn down once built: a file scrolled
 * past stays in the document, and stays findable.
 */
export function whenNearViewport(
  element: HTMLElement,
  root: HTMLElement | null,
  onNear: () => void,
): () => void {
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        observer.disconnect();
        onNear();
      }
    },
    { root, rootMargin: "1500px 0px", threshold: 0 },
  );
  observer.observe(element);
  return () => observer.disconnect();
}
