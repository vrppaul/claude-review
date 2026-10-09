/**
 * Dragging the edge of a column.
 *
 * Both the file tree and the agent panel are the reader's to size, and they
 * are sized the same way: grab the edge, or step it with the arrow keys.
 * Which direction widens depends on which side of the window the column is
 * on, and that is the only difference between them.
 */

/** Which way the column grows when the pointer moves that way. */
type Grows = 'left' | 'right';

interface Sizing {
	width: number;
	grows: Grows;
	onWidth: (width: number) => void;
}

/** How far the arrow keys move an edge at a time. */
const STEP = 24;

/** One drag of an edge, from the pointer going down until it is let go. */
class EdgeDrag {
	readonly #handle: HTMLElement;
	readonly #pointerId: number;
	readonly #startX: number;
	readonly #width: number;
	readonly #towards: number;
	readonly #onWidth: (width: number) => void;

	constructor(event: PointerEvent & { currentTarget: HTMLElement }, { width, grows, onWidth }: Sizing) {
		this.#handle = event.currentTarget;
		this.#pointerId = event.pointerId;
		this.#startX = event.clientX;
		this.#width = width;
		this.#towards = grows === 'left' ? -1 : 1;
		this.#onWidth = onWidth;
	}

	start(): void {
		this.#handle.setPointerCapture(this.#pointerId);
		this.#handle.addEventListener('pointermove', this.#moved);
		this.#handle.addEventListener('pointerup', this.#released);
	}

	readonly #moved = (moved: PointerEvent): void => {
		this.#onWidth(this.#width + this.#towards * (moved.clientX - this.#startX));
	};

	readonly #released = (): void => {
		this.#handle.removeEventListener('pointermove', this.#moved);
		this.#handle.removeEventListener('pointerup', this.#released);
	};
}

/** Follow the pointer until it is let go, reporting the width it implies. */
export function dragEdge(event: PointerEvent & { currentTarget: HTMLElement }, sizing: Sizing): void {
	new EdgeDrag(event, sizing).start();
}

/**
 * Step an edge with the arrow keys, and say whether the key was one of them.
 *
 * A drag needs a mouse; the same edge has to be movable without one.
 */
export function stepEdge(event: KeyboardEvent, { width, grows, onWidth }: Sizing): boolean {
	const towards = grows === 'left' ? -1 : 1;
	if (event.key === 'ArrowLeft') onWidth(width - towards * STEP);
	else if (event.key === 'ArrowRight') onWidth(width + towards * STEP);
	else return false;

	event.preventDefault();
	return true;
}
