/**
 * What a paste holds of images, and an image's size as the reader is told it.
 *
 * Sending them is the attachments' business; this is only reading what
 * arrived.
 */

const BYTES_PER_KILOBYTE = 1024;
const BYTES_PER_MEGABYTE = BYTES_PER_KILOBYTE * BYTES_PER_KILOBYTE;

/** The images among what was pasted. */
export function imagesAmong(files: FileList | null | undefined): File[] {
	return Array.from(files ?? []).filter((file) => file.type.startsWith('image/'));
}

/** A limit in bytes, said the way the server says it. */
export function wholeMegabytes(bytes: number): number {
	return Math.floor(bytes / BYTES_PER_MEGABYTE);
}
