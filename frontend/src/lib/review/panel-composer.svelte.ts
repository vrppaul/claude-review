/**
 * The message being written in the agent panel: its words and the images
 * pasted into it.
 *
 * Held here rather than in the panel, and kept with the draft, so hiding
 * the panel or reloading the page loses neither — and no image is left on
 * the server with nothing on screen pointing at it.
 */

import { type Draft, emptyComposer } from "$lib/drafts/draft-shapes";
import type { Composer } from "$lib/types";
import { ImageAttachments } from "$lib/utils/image-attachments.svelte";

export class PanelComposer {
  #text: string;
  readonly attachments: ImageAttachments;

  /** @param draft an unsent review of the same thing, with its half-written message */
  constructor(draft: Draft | null) {
    const kept = draft?.composer ?? emptyComposer();
    this.#text = $state(kept.text);
    this.attachments = new ImageAttachments(kept.images);
  }

  get text(): string {
    return this.#text;
  }

  /** The message as the draft keeps it. */
  get kept(): Composer {
    return {
      text: this.#text,
      images: $state.snapshot(this.attachments.images),
    };
  }

  setText(text: string): void {
    this.#text = text;
  }

  /** Take in what another tab on the same review was writing. */
  adopt(draft: Draft): void {
    this.#text = draft.composer.text;
    this.attachments.reset(draft.composer.images);
  }

  /**
   * Let go of what went out with a message. What was written or pasted
   * while it was on its way belongs to the next message, so only what went
   * is cleared.
   */
  takeSent(written: string, images: string[]): void {
    if (this.#text.startsWith(written)) {
      this.#text = this.#text.slice(written.length).trimStart();
    }
    this.attachments.release(images);
  }
}
