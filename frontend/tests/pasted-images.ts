/** Screenshots a reader pastes into a comment or a panel message. */
import { fireEvent } from '@testing-library/svelte';
import type { ImageLimits } from '$lib/types';
import { fakeServer, type FakeServer } from './fake-server';

const BYTES_PER_MEGABYTE = 1024 * 1024;

/** What the server takes in pasted images, as the diff response carries it. */
export const IMAGE_LIMITS: ImageLimits = {
	max_image_bytes: 10 * BYTES_PER_MEGABYTE,
	max_images_per_message: 10
};

/** The id the server keeps a pasted screenshot under. */
export const KEPT_AS = '4f.png';

// The first bytes of every PNG: enough for anything that looks at the type
const PNG_SIGNATURE = [0x89, 0x50, 0x4e, 0x47];
const PNG = 'image/png';

/** A small screenshot, as the clipboard hands one over. */
export function screenshot(): File {
	return new File([new Uint8Array(PNG_SIGNATURE)], 'screen.png', { type: PNG });
}

/** A screenshot one byte past what the server takes. */
export function oversizedScreenshot(): File {
	return new File([new Uint8Array(IMAGE_LIMITS.max_image_bytes + 1)], 'huge.png', { type: PNG });
}

/** Paste these files into a field, as Ctrl+V does with them on the clipboard. */
export function paste(field: HTMLElement, ...files: File[]): Promise<boolean> {
	return fireEvent.paste(field, { clipboardData: { files } });
}

/** Have the server keep every pasted image under `KEPT_AS`. */
export function keepingImages(server: FakeServer = fakeServer()): FakeServer {
	server.answer('POST /api/images', { image_id: KEPT_AS });
	return server;
}
