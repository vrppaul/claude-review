/**
 * What a paste holds of images.
 *
 * Sending them is the attachments' business; this is only reading what
 * arrived.
 */

/** The images among what was pasted. */
export function imagesAmong(files: FileList | null | undefined): File[] {
	return Array.from(files ?? []).filter((file) => file.type.startsWith('image/'));
}
