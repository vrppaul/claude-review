/**
 * Stopping what was started. Something that starts several things at once —
 * an effect, a listener, a timer — hands back one way to stop them all.
 */

/** One way to stop several things, each stopped in the order given. */
export function stopsTogether(...stops: (() => void)[]): () => void {
	return () => stops.forEach((stop) => stop());
}
