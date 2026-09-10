/**
 * Dragging the edge of a column.
 *
 * Both the file tree and the agent panel are the reader's to size, and they
 * are sized the same way: grab the edge, or step it with the arrow keys.
 * Which direction widens depends on which side of the window the column is
 * on, and that is the only difference between them.
 */

/** Which way the column grows when the pointer moves that way. */
export type Grows = "left" | "right";

interface Sizing {
  width: number;
  grows: Grows;
  onWidth: (px: number) => void;
}

/** How far the arrow keys move an edge at a time. */
const STEP = 24;

/** Follow the pointer until it is let go, reporting the width it implies. */
export function dragEdge(
  event: PointerEvent & { currentTarget: HTMLElement },
  { width, grows, onWidth }: Sizing,
): void {
  const handle = event.currentTarget;
  const startX = event.clientX;
  const towards = grows === "left" ? -1 : 1;
  handle.setPointerCapture(event.pointerId);

  function move(moved: PointerEvent) {
    onWidth(width + towards * (moved.clientX - startX));
  }
  function release() {
    handle.removeEventListener("pointermove", move);
    handle.removeEventListener("pointerup", release);
  }
  handle.addEventListener("pointermove", move);
  handle.addEventListener("pointerup", release);
}

/**
 * Step an edge with the arrow keys, and say whether the key was one of them.
 *
 * A drag needs a mouse; the same edge has to be movable without one.
 */
export function stepEdge(
  event: KeyboardEvent,
  { width, grows, onWidth }: Sizing,
): boolean {
  const towards = grows === "left" ? -1 : 1;
  if (event.key === "ArrowLeft") onWidth(width - towards * STEP);
  else if (event.key === "ArrowRight") onWidth(width + towards * STEP);
  else return false;

  event.preventDefault();
  return true;
}
