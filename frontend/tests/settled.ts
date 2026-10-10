/** Waiting out work the page goes on with after a test hands it something. */

/**
 * Let work that goes on after it was started — a retake taken in, threads
 * followed — run to its end: everything it awaits has answered by the time
 * the next task runs.
 */
export function settled(): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve));
}
