/** A size in bytes, as the reader is told one: an image too large to send, a file too large to show. */

const BYTES_PER_KILOBYTE = 1024;
const BYTES_PER_MEGABYTE = BYTES_PER_KILOBYTE * BYTES_PER_KILOBYTE;

/** A limit in bytes, said the way the server says it. */
export function wholeMegabytes(bytes: number): number {
	return Math.floor(bytes / BYTES_PER_MEGABYTE);
}
