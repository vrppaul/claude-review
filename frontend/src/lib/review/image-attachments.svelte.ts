/**
 * Images pasted into something being written, on their way to the agent.
 *
 * One implementation for every field a reader writes in: the panel's
 * message, a new comment, a reply, an edit. Each image goes to the server
 * the moment it is pasted, so what is shown under the field is exactly what
 * the agent will be able to open.
 */

import type { SendLimits } from '$lib/types';
import { SvelteSet } from 'svelte/reactivity';
import { discardImage, keepImage } from '$lib/api/review-api';
import { messageOf } from '$lib/utils/errors';
import { imagesAmong, wholeMegabytes } from '$lib/utils/images';

// What a field says when an image could not be attached and nothing said why
const ATTACHING_FAILED = 'Could not attach the image';

export class ImageAttachments {
	#images = $state<string[]>([]);
	#uploading = $state(0);
	// What this instance uploaded itself, as opposed to images it was handed
	// with an edit or a draft: the only ones it may let the server drop
	readonly #uploaded = new SvelteSet<string>();

	/** Ids the server kept the attached images under, in the order pasted. */
	get images(): readonly string[] {
		return this.#images;
	}

	/** Images still on their way to the server; sending waits for them. */
	get uploading(): number {
		return this.#uploading;
	}

	/** @param images what is already attached, when picking up a draft or an edit */
	constructor(images: string[]) {
		this.#images = images;
	}

	/**
	 * Take the images out of a paste, if it carried any.
	 *
	 * Returns the first refusal, in words the reader can act on. A paste with
	 * no image in it is left to the field: it is text.
	 */
	async takePaste(event: ClipboardEvent, limits: SendLimits): Promise<string | undefined> {
		const pasted = imagesAmong(event.clipboardData?.files);
		if (pasted.length === 0) return undefined;
		// A file copied in a file manager brings its name along as text
		event.preventDefault();
		const [refusal] = await this.attach(pasted, limits);
		return refusal;
	}

	/**
	 * Keep images on the server and attach them.
	 *
	 * Returns what was refused. The limits are the server's own, so nothing
	 * is uploaded only to be turned away.
	 */
	async attach(files: File[], limits: SendLimits): Promise<string[]> {
		// Refused by size before counting, so an image that will never be sent
		// does not take the place of one that would
		const fitting = files.filter((file) => file.size <= limits.max_image_bytes);
		const refusals =
			fitting.length < files.length ? [`The image is over ${wholeMegabytes(limits.max_image_bytes)} MB`] : [];
		const room = Math.max(0, limits.max_images_per_message - this.#images.length - this.#uploading);
		if (fitting.length > room) {
			refusals.push(`At most ${limits.max_images_per_message} images at a time`);
		}
		const failures = await Promise.all(fitting.slice(0, room).map((file) => this.#attachOne(file)));
		return [...refusals, ...failures.filter((failure): failure is string => failure !== null)];
	}

	/** Take an image off, and off the server unless the agent may know of it. */
	detach(imageId: string) {
		this.forget(imageId);
		void letServerDrop(imageId);
	}

	/** Take an image off without asking the server: it no longer has it. */
	forget(imageId: string) {
		this.#images = this.#images.filter((kept) => kept !== imageId);
	}

	/** Let go of what went out with a message; what was pasted since stays. */
	release(sent: string[]) {
		this.#images = this.#images.filter((imageId) => !sent.includes(imageId));
	}

	/**
	 * Let the server drop what this field uploaded, when it closes unsent.
	 *
	 * Only those: an image handed in with an edit may already have reached
	 * the agent, and the server keeps those anyway.
	 */
	abandon() {
		for (const imageId of this.#images) {
			if (this.#uploaded.has(imageId)) void letServerDrop(imageId);
		}
		this.#images = [];
	}

	async #attachOne(file: File): Promise<string | null> {
		this.#uploading += 1;
		try {
			const { image_id: imageId } = await keepImage(file);
			this.#uploaded.add(imageId);
			this.#images = [...this.#images, imageId];
			return null;
		} catch (error) {
			return messageOf(error, ATTACHING_FAILED);
		} finally {
			this.#uploading -= 1;
		}
	}
}

/**
 * Let the server drop an image nothing points at any more.
 *
 * Best effort: whatever is left behind goes with the review when it ends.
 */
async function letServerDrop(imageId: string): Promise<void> {
	try {
		await discardImage(imageId);
	} catch {
		// The review's workspace is removed at the end either way
	}
}
