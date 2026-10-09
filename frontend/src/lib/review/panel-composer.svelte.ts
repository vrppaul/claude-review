/**
 * The message being written in the agent panel: its words and the images
 * pasted into it.
 *
 * Held here rather than in the panel, and saved with the draft, so hiding
 * the panel or reloading the page loses neither — and no image is left on
 * the server with nothing on screen pointing at it.
 */

import type { Composer } from "$lib/types";
import { type Draft, saveDraft } from "$lib/utils/drafts";
import { ImageAttachments } from "$lib/utils/image-attachments.svelte";

export class PanelComposer {
  readonly #title: string;
  #text: string;
  readonly attachments: ImageAttachments;

  /**
   * @param title what the review is of, which its draft is kept under
   * @param draft an unsent review of the same thing, with its half-written message
   */
  constructor(title: string, draft: Draft | null) {
    this.#title = title;
    const kept = draft?.composer;
    this.#text = $state(kept?.text ?? "");
    this.attachments = new ImageAttachments(kept?.images ?? [], () =>
      this.#remember(),
    );
  }

  get text(): string {
    return this.#text;
  }

  setText(text: string): void {
    this.#text = text;
    this.#remember();
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

  #remember(): void {
    const composer: Composer = {
      text: this.#text,
      images: $state.snapshot(this.attachments.images),
    };
    saveDraft({ title: this.#title, composer });
  }
}
