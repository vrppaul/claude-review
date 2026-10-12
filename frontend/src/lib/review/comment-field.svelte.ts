/**
 * A comment being written, and not said yet: its words, how it is meant,
 * and the images pasted into it.
 *
 * Held by the review rather than by the field that shows it, so the field
 * can go and come back — a file folded and opened, the layout switched, the
 * page reloaded — with everything still in it.
 */

import type { KeptField } from '$lib/drafts/draft-shapes';
import { ImageAttachments } from '$lib/review/image-attachments.svelte';
import type { CommentSeverity, WrittenAt } from '$lib/types';

/** What a comment field is known by: where it is written. */
export function fieldKey(at: WrittenAt): string {
	if (at.kind !== 'new') return `${at.kind}:${at.thread}`;
	const { side, startLine, endLine } = at.lines;
	return `new:${at.file}:${side}:${startLine}-${endLine}`;
}

/**
 * How a field came to be on the page: opened by the reader just now, or
 * brought back by a reload. One just opened takes the cursor; one brought
 * back leaves the cursor where it is.
 */
type FieldOpening = 'opened' | 'restored';

/** What a field began from: what it was opened with — nothing, or the comment being edited. */
export type BeganFrom = Pick<KeptField, 'text' | 'severity' | 'images'>;

/** Whether two lists of images hold the same images, in the same order. */
function sameImages(one: readonly string[], other: readonly string[]): boolean {
	return one.length === other.length && one.every((image, position) => image === other[position]);
}

export class CommentField<Written extends WrittenAt = WrittenAt> {
	/** Where it is written. */
	readonly at: Written;
	readonly key: string;
	readonly attachments: ImageAttachments;
	#text: string;
	// What it began from. Whatever differs from it is the reader's own: it is
	// not dropped unasked, and an edit holding none of it says nothing new
	readonly #beganFrom: BeganFrom;
	// A reply has no weight of its own — the thread's belongs to its first
	// comment — so a reply's field keeps one all the same, never shown
	#severity: CommentSeverity;
	// Whether the field should take the cursor when it is next drawn: when it
	// is opened, or asked for again, but not when it is merely drawn again
	#focusWanted: boolean;

	/**
	 * @param at where it is written
	 * @param kept what it holds: nothing yet, what is being edited, or what a draft kept
	 * @param opening whether the reader opened it just now, or a reload brought it back
	 * @param beganFrom what it was opened with: for a field brought back, what its opener knows of it
	 */
	constructor(at: Written, kept: Omit<KeptField, 'at'>, opening: FieldOpening, beganFrom: BeganFrom) {
		this.at = at;
		this.key = fieldKey(at);
		this.attachments = new ImageAttachments(kept.images, kept.uploaded);
		this.#text = $state(kept.text);
		this.#severity = $state(kept.severity);
		this.#beganFrom = beganFrom;
		this.#focusWanted = $state(opening === 'opened');
	}

	get text(): string {
		return this.#text;
	}

	set text(text: string) {
		this.#text = text;
	}

	get severity(): CommentSeverity {
		return this.#severity;
	}

	set severity(severity: CommentSeverity) {
		this.#severity = severity;
	}

	/** Whether it holds something to say — words, or an image — with no image still on its way. */
	get sayable(): boolean {
		return (this.#text.trim().length > 0 || this.attachments.images.length > 0) && this.attachments.uploading === 0;
	}

	/**
	 * Whether it holds something the reader put in it: words, a weight or
	 * images other than those it began from, or an image still on its way.
	 * Putting it away would lose that; an edit holding none of it is left as
	 * it was, and says nothing its thread does not say already.
	 */
	get holdsWork(): boolean {
		const began = this.#beganFrom;
		return (
			this.#text.trim() !== began.text.trim() ||
			this.#severity !== began.severity ||
			!sameImages(this.attachments.images, began.images) ||
			this.attachments.uploading > 0
		);
	}

	/** Whether it should take the cursor now. */
	get focusWanted(): boolean {
		return this.#focusWanted;
	}

	/** Put the cursor in it as soon as it is drawn. */
	askForFocus(): void {
		this.#focusWanted = true;
	}

	/** It has the cursor. */
	focusTaken(): void {
		this.#focusWanted = false;
	}

	/** The field as the draft keeps it. */
	get kept(): KeptField {
		return {
			at: this.at,
			text: this.#text,
			severity: this.#severity,
			images: [...this.attachments.images],
			uploaded: this.attachments.uploaded
		};
	}
}
