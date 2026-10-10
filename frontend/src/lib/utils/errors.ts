/** What went wrong, in the words it went wrong with, or what to say when it gave none. */
export function messageOf(error: unknown, fallback: string): string {
	return error instanceof Error ? error.message : fallback;
}
