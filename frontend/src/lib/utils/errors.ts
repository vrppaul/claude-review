/**
 * What went wrong, in the words it went wrong with.
 *
 * Every request says its own failure in words (`api/request.ts`): what the
 * page was doing, and the server's reason, its status, or that it did not
 * answer. Nothing else throws anything but an error, so what is not one is
 * said as it is.
 */
export function messageOf(error: unknown): string {
	return error instanceof Error ? error.message : String(error);
}
