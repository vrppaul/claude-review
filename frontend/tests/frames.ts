/**
 * Waiting out the page taking the reader somewhere. A jump scrolls at once,
 * scrolls once more a few frames on, where what was built around what it
 * scrolled to has pushed it, and comes to rest the frame after; so a test of
 * where it ends lets frames go by. jsdom lays nothing out, and moves nothing
 * itself.
 */

// Enough frames for a jump to come to rest: it puts what it scrolled to right in its third frame, and
// comes to rest in its fourth
const FRAMES_TO_COME_TO_REST = 4;

/** Let a jump come to rest. */
export async function frames(count = FRAMES_TO_COME_TO_REST): Promise<void> {
	for (let frame = 0; frame < count; frame += 1) {
		await new Promise((resolve) => requestAnimationFrame(resolve));
	}
}
