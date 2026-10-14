/**
 * What is being written in the threads, and not said yet: comments started
 * on lines or on a block of the story's words, replies, and edits of the
 * comment that opened a thread.
 *
 * Several comments can be started on one file, each on its own lines; a
 * block of the story has one at a time, and a thread one reply and one
 * edit. Each stays until its words are added, asked or put away — not when
 * its field stops being drawn — and the draft keeps them across a reload.
 * What happens to each is told to whoever follows the comment fields: the
 * tour.
 */

import { SvelteMap } from 'svelte/reactivity';

import type { KeptField } from '$lib/drafts/draft-shapes';
import { type BeganFrom, blockFieldKey, CommentField, fieldKey } from '$lib/review/comment-field.svelte';
import type { CommentFields } from '$lib/review/comment-fields';
import type { CommentFieldEvent, PickedLines, StoryBlock, Thread, WrittenAt, WrittenOnLines } from '$lib/types';

/** How a field can go: its words added to the review, asked straight away, or put away unsaid. */
type Ending = Exclude<CommentFieldEvent['type'], 'opened'>;

/** What a field opens with when nothing is written in it yet. */
function nothingWritten(): Omit<KeptField, 'at'> {
	return { text: '', severity: 'note', images: [], uploaded: [] };
}

/** What a field begins from when it opens holding this. */
function beganFrom({ text, severity, images }: Omit<KeptField, 'at'>): BeganFrom {
	return { text, severity, images: [...images] };
}

/**
 * What a field a reload brought back began from: an edit, from its thread
 * as the draft kept it, which the edit has not touched yet; anything else,
 * from nothing.
 */
function beganBefore(at: WrittenAt, threads: readonly Thread[]): BeganFrom {
	const edited = at.kind === 'edit' ? threads.find((thread) => thread.id === at.thread) : undefined;
	if (edited === undefined) return beganFrom(nothingWritten());
	return { text: edited.body, severity: edited.severity, images: [...edited.images] };
}

function isOnLines(field: CommentField): field is CommentField<WrittenOnLines> {
	return field.at.kind === 'new';
}

export class ThreadWriting {
	// Every field being written, by where it is written, in the order opened
	readonly #fields = new SvelteMap<string, CommentField>();
	readonly #events: CommentFields;

	/**
	 * @param kept what was being written when the draft was kept
	 * @param events where what happens to a field is told
	 * @param threads the threads as the draft kept them, which an edit kept with them began from
	 */
	constructor(kept: KeptField[], events: CommentFields, threads: readonly Thread[]) {
		this.#events = events;
		// Drawn again where they were, without taking the cursor from wherever the reader is
		for (const field of kept) {
			const restored = new CommentField(field.at, field, 'restored', beganBefore(field.at, threads));
			this.#fields.set(restored.key, restored);
		}
	}

	/** Every field being written, in the order opened. */
	get fields(): CommentField[] {
		return [...this.#fields.values()];
	}

	/** The comments being started on a file's lines, in the order they were started. */
	onLinesOf(file: string): CommentField<WrittenOnLines>[] {
		return [...this.#fields.values()].filter(isOnLines).filter((field) => field.at.file === file);
	}

	/** How many comments are being started on lines, in every file. */
	get openOnLines(): number {
		return [...this.#fields.values()].filter(isOnLines).length;
	}

	/**
	 * Start a comment on lines of a file — or bring back the one already being written on them.
	 *
	 * @param quote what the lines say as they are picked
	 */
	pickLines(file: string, lines: PickedLines, quote: string[]): void {
		this.#open({ kind: 'new', file, lines, quote }, nothingWritten());
	}

	/**
	 * Start a comment on a block of the story's words — or bring back the one already being written on it.
	 *
	 * @param words what the block says as the reader asks about it
	 */
	askAbout(block: StoryBlock, words: string): void {
		this.#open({ kind: 'story', block, words }, nothingWritten());
	}

	/** The comment being written on a block of the story, if one is. */
	aboutBlock(block: StoryBlock): CommentField | undefined {
		return this.#fields.get(blockFieldKey(block));
	}

	/** The reply being written in a thread, if one is. */
	reply(thread: string): CommentField | undefined {
		return this.#fields.get(fieldKey({ kind: 'reply', thread }));
	}

	openReply(thread: string): void {
		this.#open({ kind: 'reply', thread }, nothingWritten());
	}

	/** The edit being made of a thread's opening comment, if one is. */
	edit(thread: string): CommentField | undefined {
		return this.#fields.get(fieldKey({ kind: 'edit', thread }));
	}

	/** Start editing a thread's opening comment, from what it says now. */
	openEdit(thread: Thread): void {
		this.#open(
			{ kind: 'edit', thread: thread.id },
			// The thread's images are handed in: the field did not upload them, and lets none go
			{ text: thread.body, severity: thread.severity, images: [...thread.images], uploaded: [] }
		);
	}

	/** Its words went into the review: the field goes, and what was pasted into it stays with them. */
	added(field: CommentField): void {
		this.#end(field, 'added');
	}

	/** Its words were handed straight to whoever is answering. */
	asked(field: CommentField): void {
		this.#end(field, 'asked');
	}

	/** Put away unsaid: what the field uploaded itself is let go. */
	discard(field: CommentField): void {
		field.attachments.abandon();
		this.#end(field, 'closed');
	}

	/** A thread is gone, and whatever was being written in it goes too. */
	forget(thread: string): void {
		for (const field of [this.reply(thread), this.edit(thread)]) {
			if (field) this.discard(field);
		}
	}

	/** Every field being written, as the draft keeps them. */
	get kept(): KeptField[] {
		return [...this.#fields.values()].map((field) => field.kept);
	}

	/** Open a field — or, where one is already open, bring it back to the reader. */
	#open(at: WrittenAt, written: Omit<KeptField, 'at'>): void {
		const open = this.#fields.get(fieldKey(at));
		if (open) {
			open.askForFocus();
			return;
		}
		const field = new CommentField(at, written, 'opened', beganFrom(written));
		this.#fields.set(field.key, field);
		this.#events.report({ type: 'opened', kind: at.kind });
	}

	#end(field: CommentField, ending: Ending): void {
		this.#fields.delete(field.key);
		this.#events.report({ type: ending, kind: field.at.kind });
	}
}
