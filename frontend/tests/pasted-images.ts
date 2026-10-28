/** Screenshots a reader pastes into a comment or a panel message. */
import { fireEvent } from '@testing-library/svelte';
import type { SendLimits } from '$lib/types';
import { fakeServer, type FakeServer } from './fake-server';

const BYTES_PER_MEGABYTE = 1024 * 1024;

/** What the server takes, as the diff response carries it. */
export const SEND_LIMITS: SendLimits = {
	max_image_bytes: 10 * BYTES_PER_MEGABYTE,
	max_images_per_message: 10,
	max_quoted_lines: 200,
	max_window_lines: 2000,
	max_text_length: 50_000,
	max_feedback_length: 49_000,
	largest_file_shown_bytes: 4 * BYTES_PER_MEGABYTE
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
	return new File([new Uint8Array(SEND_LIMITS.max_image_bytes + 1)], 'huge.png', { type: PNG });
}

/** Paste these files into a field, as Ctrl+V does with them on the clipboard. */
export function paste(field: HTMLElement, ...files: File[]): Promise<boolean> {
	return fireEvent.paste(field, { clipboardData: { files } });
}

/** Have the server keep every pasted image under `KEPT_AS`, and let one go when the page asks it to. */
export function keepingImages(server: FakeServer = fakeServer()): FakeServer {
	server.answer('POST /api/images', { image_id: KEPT_AS });
	server.answer('DELETE /api/images/{image_id}', null);
	return server;
}
