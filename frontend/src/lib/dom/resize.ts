/**
 * Dragging the edge of a column.
 *
 * Both the file tree and the agent panel are the reader's to size, and they
 * are sized the same way: grab the edge, or step it with the arrow keys.
 * Which direction widens depends on which side of the window the column is
 * on, and that is the only difference between them.
 */

/** Which way the column grows when the pointer moves that way. */
export type Grows = 'left' | 'right';

/** A column the reader sizes: how wide it is, and how it is made another width. */
export interface ColumnWidth {
	readonly width: number;
	setWidth: (next: number) => void;
}

/** How far the arrow keys move an edge at a time. */
const STEP = 24;

// Which way along the screen a column's width runs, as the pointer's position does
const ALONG: Record<Grows, number> = { left: -1, right: 1 };

/** One drag of an edge, from the pointer going down until it is let go. */
class EdgeDrag {
	readonly #handle: HTMLElement;
	readonly #pointerId: number;
	readonly #startX: number;
	readonly #startWidth: number;
	readonly #along: number;
	readonly #column: ColumnWidth;

	constructor(event: PointerEvent & { currentTarget: HTMLElement }, column: ColumnWidth, grows: Grows) {
		this.#handle = event.currentTarget;
		this.#pointerId = event.pointerId;
		this.#startX = event.clientX;
		this.#startWidth = column.width;
		this.#along = ALONG[grows];
		this.#column = column;
	}

	start(): void {
		this.#handle.setPointerCapture(this.#pointerId);
		this.#handle.addEventListener('pointermove', this.#moved);
		this.#handle.addEventListener('pointerup', this.#released);
	}

	readonly #moved = (moved: PointerEvent): void => {
		this.#column.setWidth(this.#startWidth + this.#along * (moved.clientX - this.#startX));
	};

	readonly #released = (): void => {
		this.#handle.removeEventListener('pointermove', this.#moved);
		this.#handle.removeEventListener('pointerup', this.#released);
	};
}

/** Follow the pointer until it is let go, sizing the column as it goes. */
export function dragEdge(
	event: PointerEvent & { currentTarget: HTMLElement },
	column: ColumnWidth,
	grows: Grows
): void {
	new EdgeDrag(event, column, grows).start();
}

/**
 * Step an edge with the arrow keys, and say whether the key was one of them.
 *
 * A drag needs a mouse; the same edge has to be movable without one.
 */
export function stepEdge(event: KeyboardEvent, column: ColumnWidth, grows: Grows): boolean {
	if (event.key === 'ArrowLeft') column.setWidth(column.width - ALONG[grows] * STEP);
	else if (event.key === 'ArrowRight') column.setWidth(column.width + ALONG[grows] * STEP);
	else return false;

	event.preventDefault();
	return true;
}
