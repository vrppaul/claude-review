/**
 * A part of the page that fails to draw — a file, the panel — is put aside
 * on its own, so the rest of the review stays on screen and in reach. What
 * broke it is still told, whole, to whoever looks in the console.
 */
export function reportBroken(error: unknown): void {
	console.error('claude-review: a part of the page could not be drawn', error);
}
