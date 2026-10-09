/**
 * Two tabs on one review, each changing the draft: what one keeps is taken
 * in by the other without wiping what that one has not kept yet.
 *
 * Merged three ways, part by part: from the draft this tab last kept or took
 * in (the base), what this tab changed since (mine) is laid over what the
 * other tab kept (theirs). Threads, turns, marks and sends are merged by id;
 * the summary and the half-written message are each taken whole. A thread
 * changed in both tabs since the base is taken as this tab has it.
 */

import type { Draft } from '$lib/drafts/draft-shapes';
import { emptyComposer } from '$lib/drafts/draft-shapes';
import { COMMENT_ID_PREFIX, IdSequence } from '$lib/utils/ids';
import { laterPosition } from '$lib/utils/telling';

/** Whether two parts of a draft say the same; a draft is plain data. */
function same(first: unknown, second: unknown): boolean {
	return JSON.stringify(first) === JSON.stringify(second);
}

/** Whether two drafts say the same. */
export function sameDraft(first: Draft, second: Draft): boolean {
	return same(first, second);
}

/** Theirs, with what mine added, changed or removed since the base laid over it. */
function mergeKeyed<Value>(
	base: ReadonlyMap<string, Value>,
	mine: ReadonlyMap<string, Value>,
	theirs: ReadonlyMap<string, Value>
): Map<string, Value> {
	const merged = new Map(theirs);
	for (const [key, value] of mine) {
		if (!same(base.get(key), value)) merged.set(key, value);
	}
	for (const key of base.keys()) {
		if (!mine.has(key)) merged.delete(key);
	}
	return merged;
}

function byId<Item extends { id: string }>(items: readonly Item[]): Map<string, Item> {
	return new Map(items.map((item) => [item.id, item]));
}

function asMarks(ids: readonly string[]): Map<string, true> {
	return new Map(ids.map((id) => [id, true]));
}

/** Mine where this tab changed it since the base, theirs where it did not. */
function mineIfChanged<Part>(base: Part, mine: Part, theirs: Part): Part {
	return same(base, mine) ? theirs : mine;
}

/** An id, or the one it is renamed to if it is the one renamed. */
function renamedId(id: string, from: string, to: string): string {
	return id === from ? to : id;
}

/** A draft with one thread called by another id, everywhere the draft names it. */
function renamed(draft: Draft, from: string, to: string): Draft {
	return {
		...draft,
		threads: draft.threads.map((thread) => (thread.id === from ? { ...thread, id: to } : thread)),
		read: {
			folded: draft.read.folded.map((id) => renamedId(id, from, to)),
			unread: draft.read.unread.map((id) => renamedId(id, from, to)),
			awaiting: draft.read.awaiting.map(([id, questions]) => [renamedId(id, from, to), questions])
		},
		sent: draft.sent.map(([id, round]) => [renamedId(id, from, to), round])
	};
}

/**
 * Mine, with every thread the reader wrote in both tabs under the same id
 * since the base given an id of its own: each tab hands out ids from the
 * same count. A thread the agent raised is named by the server, and both
 * tabs holding it under one id hold the same thread, told to each.
 */
function apartFrom(base: Draft, mine: Draft, theirs: Draft): Draft {
	const baseIds = new Set(base.threads.map((thread) => thread.id));
	const theirThreads = byId(theirs.threads);
	const ids = new IdSequence(COMMENT_ID_PREFIX);
	ids.continueFrom(Math.max(mine.issued.comments, theirs.issued.comments));
	let apart = mine;
	for (const thread of mine.threads) {
		const theirsUnderIt = theirThreads.get(thread.id);
		const clashes = thread.raised_by === 'reader' && theirsUnderIt !== undefined && !same(theirsUnderIt, thread);
		if (clashes && !baseIds.has(thread.id)) apart = renamed(apart, thread.id, ids.next());
	}
	return { ...apart, issued: { ...apart.issued, comments: Math.max(apart.issued.comments, ids.issued) } };
}

/** A draft holding nothing: the base of a tab that has kept and taken in nothing yet. */
export function emptyDraftLike(draft: Draft): Draft {
	return {
		...draft,
		threads: [],
		read: { folded: [], unread: [], awaiting: [] },
		reviewBody: '',
		sent: [],
		panel: [],
		composer: emptyComposer(),
		told: null
	};
}

/** The draft both tabs hold once this tab takes in what the other kept, keeping what it has not kept yet. */
export function mergeDrafts(base: Draft, unmerged: Draft, theirs: Draft): Draft {
	const mine = apartFrom(base, unmerged, theirs);
	return {
		...theirs,
		threads: [...mergeKeyed(byId(base.threads), byId(mine.threads), byId(theirs.threads)).values()],
		read: {
			folded: [...mergeKeyed(asMarks(base.read.folded), asMarks(mine.read.folded), asMarks(theirs.read.folded)).keys()],
			unread: [...mergeKeyed(asMarks(base.read.unread), asMarks(mine.read.unread), asMarks(theirs.read.unread)).keys()],
			awaiting: [...mergeKeyed(new Map(base.read.awaiting), new Map(mine.read.awaiting), new Map(theirs.read.awaiting))]
		},
		reviewBody: mineIfChanged(base.reviewBody, mine.reviewBody, theirs.reviewBody),
		sent: [...mergeKeyed(new Map(base.sent), new Map(mine.sent), new Map(theirs.sent))],
		panel: [...mergeKeyed(byId(base.panel), byId(mine.panel), byId(theirs.panel)).values()],
		composer: mineIfChanged(base.composer, mine.composer, theirs.composer),
		issued: {
			comments: Math.max(mine.issued.comments, theirs.issued.comments),
			turns: Math.max(mine.issued.turns, theirs.issued.turns)
		},
		told: mine.told === null ? theirs.told : laterPosition(mine.told, theirs.told)
	};
}
