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

// Long enough to find what was pointed at, short enough not to become part
// of how the file looks
const MARKED_FOR = 2000;

/**
 * Bring a file into view and mark it for a moment.
 *
 * Somebody else moved this screen, so the file has to say "here" when it
 * arrives: a page that has jumped somewhere without a word leaves the
 * reader working out what they are looking at.
 */
export function showFile(path: string): void {
  const section = sections.get(path);
  if (!section) return;

  section.scrollIntoView({ behavior: "smooth", block: "start" });
  section.classList.add("cr-marked");
  setTimeout(() => section.classList.remove("cr-marked"), MARKED_FOR);
}

/**
 * Bring a comment into view, building its file first if need be.
 *
 * A file's rows are only built once it has been near the viewport, so a
 * comment further down the review — restored from a draft, say — has no
 * element yet. Scrolling to the file makes one appear, and the comment can
 * be reached on the next frame.
 */
export function scrollToComment(commentId: string, file?: string): void {
  const found = document.getElementById(commentId);
  if (found) {
    found.scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }

  if (file === undefined) return;
  scrollToFile(file);
  requestAnimationFrame(() =>
    document
      .getElementById(commentId)
      ?.scrollIntoView({ behavior: "smooth", block: "center" }),
  );
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
