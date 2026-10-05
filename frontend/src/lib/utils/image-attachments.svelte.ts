/**
 * Images pasted into something being written, on their way to the agent.
 *
 * One implementation for every field a reader writes in: the panel's
 * message, a new comment, a reply, an edit. Each image goes to the server
 * the moment it is pasted, so what is shown under the field is exactly what
 * the agent will be able to open.
 */

import type { ImageLimits } from "$lib/types";
import { SvelteSet } from "svelte/reactivity";
import {
  discardImage,
  imagesAmong,
  uploadImage,
  wholeMegabytes,
} from "$lib/utils/images";

export class ImageAttachments {
  /** Ids the server kept the attached images under, in the order pasted. */
  images = $state<string[]>([]);
  /** Images still on their way to the server; sending waits for them. */
  uploading = $state(0);
  readonly #onChange: (() => void) | undefined;
  // What this instance uploaded itself, as opposed to images it was handed
  // with an edit or a draft: the only ones it may let the server drop
  readonly #uploaded = new SvelteSet<string>();

  /**
   * @param images what is already attached, when picking up a draft or an edit
   * @param onChange called whenever the attached images change, to save them
   */
  constructor(images: string[], onChange?: () => void) {
    this.images = images;
    this.#onChange = onChange;
  }

  /**
   * Take the images out of a paste, if it carried any.
   *
   * Returns the first refusal, in words the reader can act on. A paste with
   * no image in it is left to the field: it is text.
   */
  async takePaste(
    event: ClipboardEvent,
    limits: ImageLimits | null,
  ): Promise<string | undefined> {
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
  async attach(files: File[], limits: ImageLimits | null): Promise<string[]> {
    if (!limits) return ["The review has not finished loading"];

    // Refused by size before counting, so an image that will never be sent
    // does not take the place of one that would
    const fitting = files.filter((file) => file.size <= limits.max_image_bytes);
    const refusals =
      fitting.length < files.length
        ? [`The image is over ${wholeMegabytes(limits.max_image_bytes)} MB`]
        : [];
    const room = Math.max(
      0,
      limits.max_images_per_message - this.images.length - this.uploading,
    );
    if (fitting.length > room) {
      refusals.push(
        `At most ${limits.max_images_per_message} images at a time`,
      );
    }
    const failures = await Promise.all(
      fitting.slice(0, room).map((file) => this.#attachOne(file)),
    );
    return [
      ...refusals,
      ...failures.filter((failure): failure is string => failure !== null),
    ];
  }

  /** Take an image off, and off the server unless the agent may know of it. */
  detach(imageId: string) {
    this.forget(imageId);
    void discardImage(imageId);
  }

  /** Take an image off without asking the server: it no longer has it. */
  forget(imageId: string) {
    this.images = this.images.filter((kept) => kept !== imageId);
    this.#onChange?.();
  }

  /** Let go of what went out with a message; what was pasted since stays. */
  release(sent: string[]) {
    this.images = this.images.filter((imageId) => !sent.includes(imageId));
    this.#onChange?.();
  }

  /**
   * Let the server drop what this field uploaded, when it closes unsent.
   *
   * Only those: an image handed in with an edit may already have reached
   * the agent, and the server keeps those anyway.
   */
  abandon() {
    for (const imageId of this.images) {
      if (this.#uploaded.has(imageId)) void discardImage(imageId);
    }
    this.images = [];
  }

  /**
   * Start over with these images, as when a draft is picked up.
   *
   * Uploads still on their way keep their count: each takes itself off it
   * when it lands, and zeroing it here would leave it below nothing.
   */
  reset(images: string[]) {
    this.images = images;
  }

  async #attachOne(file: File): Promise<string | null> {
    this.uploading += 1;
    try {
      const imageId = await uploadImage(file);
      this.#uploaded.add(imageId);
      this.images = [...this.images, imageId];
      this.#onChange?.();
      return null;
    } catch (e) {
      return e instanceof Error ? e.message : "Could not attach the image";
    } finally {
      this.uploading -= 1;
    }
  }
}
