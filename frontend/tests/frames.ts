/**
 * Waiting out the page taking the reader somewhere. A jump looks once a
 * frame until what it scrolled to has stopped moving, so a test of where it
 * ends lets frames go by; jsdom lays nothing out, and moves nothing itself.
 */

// Enough frames for the settling watch, which looks once a frame until
// nothing has moved for two of them
export const FRAMES_TO_SETTLE = 6;
// Longer than a glide is given to begin, in milliseconds: what has not moved by then had nowhere to go
const A_GLIDE_HAS_BEGUN_BY = 300;

/** Let the settling watch run. */
export async function frames(count = FRAMES_TO_SETTLE): Promise<void> {
	for (let frame = 0; frame < count; frame += 1) {
		await new Promise((resolve) => requestAnimationFrame(resolve));
	}
}

/** Wait out the time a glide is given to begin, then let the settling watch run: for what stands where it is sent already. */
export async function untilAGlideWouldHaveBegun(): Promise<void> {
	await new Promise((resolve) => setTimeout(resolve, A_GLIDE_HAS_BEGUN_BY));
	await frames();
}
