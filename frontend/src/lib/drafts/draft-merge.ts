/**
 * Two tabs on one review, each changing the draft: what one keeps is taken
 * in by the other without wiping what that one has not kept yet.
 *
 * Merged three ways, part by part: from the draft both started from (the
 * base), what this tab changed since (mine) is laid over what is kept now
 * (theirs). Threads, marks, sends and panel turns are merged by id; the
 * summary and the half-written message are each taken whole. A thread both
 * changed is merged field by field, and keeps every turn either holds. What
 * one push brought — an answer, a note — is the same in both tabs; anything
 * else both added under one id is two things, and mine is given an id of
 * its own.
 */

import type { Draft } from '$lib/drafts/draft-shapes';
import { emptyComposer } from '$lib/drafts/draft-shapes';
import type { PanelTurn, TellingPosition, Thread, Turn } from '$lib/types';
import { COMMENT_ID_PREFIX, IdSequence, TURN_ID_PREFIX } from '$lib/utils/ids';
import { furtherByRun, samePosition } from '$lib/utils/telling';

// What ends the kind an id names and begins its number: `event-3`
const ID_NUMBER_FOLLOWS = '-';

/** Whether two parts of a draft say the same; a draft is plain data. */
function same(first: unknown, second: unknown): boolean {
	return JSON.stringify(first) === JSON.stringify(second);
}

/** Whether two drafts say the same. */
export function sameDraft(first: Draft, second: Draft): boolean {
	return same(first, second);
}

/** Of an item both sides changed since the base, mine. */
function keepMine<Value>(_base: Value | undefined, mine: Value): Value {
	return mine;
}

/**
 * Theirs, with what mine added, changed or removed since the base laid
 * over it. An item both changed since the base, or both added differently,
 * is what `both` makes of the two.
 */
function mergeKeyed<Value>(
	base: ReadonlyMap<string, Value>,
	mine: ReadonlyMap<string, Value>,
	theirs: ReadonlyMap<string, Value>,
	both: (base: Value | undefined, mine: Value, theirs: Value) => Value = keepMine
): Map<string, Value> {
	const merged = new Map(theirs);
	for (const [key, value] of mine) {
		const before = base.get(key);
		if (same(before, value)) continue;
		const theirValue = theirs.get(key);
		const theyChangedToo = theirValue !== undefined && !same(before, theirValue) && !same(theirValue, value);
		merged.set(key, theyChangedToo ? both(before, value, theirValue) : value);
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
function mineIfChanged<Part>(base: Part | undefined, mine: Part, theirs: Part): Part {
	return same(base, mine) ? theirs : mine;
}

/** Something said in a thread or the panel, which a push may have brought. */
interface Said {
	pushedAt?: TellingPosition;
}

/** Whether two things said are one: what one push brought, or the same thing said once. */
function sameSaid(first: Said, second: Said): boolean {
	if (first.pushedAt && second.pushedAt) return samePosition(first.pushedAt, second.pushedAt);
	return same(first, second);
}

/**
 * Every turn either side holds, once, in the order said. Turns are only
 * ever added; one this tab wrote under an id the other gave a different
 * turn is given an id of its own.
 */
function everyTurn(mine: readonly Turn[], theirs: readonly Turn[], turnIds: IdSequence): Turn[] {
	const turns = [...theirs];
	for (const turn of mine) {
		if (theirs.some((their) => sameSaid(their, turn))) continue;
		const clashes = theirs.some((their) => their.id === turn.id);
		turns.push(clashes ? { ...turn, id: turnIds.next() } : turn);
	}
	return turns.sort((first, second) => (first.at ?? 0) - (second.at ?? 0));
}

/**
 * A thread both tabs changed since the base, or both took in: each field
 * as the tab that changed it has it, mine where both did, and every turn
 * either holds.
 */
function mergedThread(base: Thread | undefined, mine: Thread, theirs: Thread, turnIds: IdSequence): Thread {
	return {
		...theirs,
		anchor: mineIfChanged(base?.anchor, mine.anchor, theirs.anchor),
		severity: mineIfChanged(base?.severity, mine.severity, theirs.severity),
		body: mineIfChanged(base?.body, mine.body, theirs.body),
		images: mineIfChanged(base?.images, mine.images, theirs.images),
		resolved: mineIfChanged(base?.resolved, mine.resolved, theirs.resolved),
		turns: everyTurn(mine.turns, theirs.turns, turnIds)
	};
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
function threadsApart(base: Draft, mine: Draft, theirs: Draft): Draft {
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

/** A fresh id of the same kind as one, past every id already given. */
function freshIdLike(id: string, given: readonly string[]): string {
	const ids = new IdSequence(id.slice(0, id.lastIndexOf(ID_NUMBER_FOLLOWS) + 1));
	ids.continuePast(given);
	return ids.next();
}

/**
 * Mine, with every panel turn this tab added since the base under an id
 * the other tab gave a different turn given an id of its own: each tab
 * counts its panel ids itself.
 */
function panelApart(base: Draft, mine: Draft, theirs: Draft): Draft {
	const baseIds = new Set(base.panel.map((turn) => turn.id));
	const theirTurns = byId(theirs.panel);
	const given = [...mine.panel, ...theirs.panel].map((turn) => turn.id);
	const panel: PanelTurn[] = [];
	for (const turn of mine.panel) {
		const theirsUnderIt = theirTurns.get(turn.id);
		const clashes = theirsUnderIt !== undefined && !sameSaid(theirsUnderIt, turn) && !baseIds.has(turn.id);
		if (!clashes) {
			panel.push(turn);
			continue;
		}
		const fresh = freshIdLike(turn.id, given);
		given.push(fresh);
		panel.push({ ...turn, id: fresh });
	}
	return { ...mine, panel };
}

/** A draft holding nothing: the base of a tab that opened from no draft and has kept nothing yet. */
export function emptyDraftLike(draft: Draft): Draft {
	return {
		...draft,
		threads: [],
		read: { folded: [], unread: [], awaiting: [] },
		reviewBody: '',
		sent: [],
		panel: [],
		composer: emptyComposer(),
		told: {}
	};
}

/** The draft both tabs hold once this tab's is merged into the kept one, keeping what it has not kept yet. */
export function mergeDrafts(base: Draft, unmerged: Draft, theirs: Draft): Draft {
	const mine = panelApart(base, threadsApart(base, unmerged, theirs), theirs);
	const turnIds = new IdSequence(TURN_ID_PREFIX);
	turnIds.continueFrom(Math.max(mine.issued.turns, theirs.issued.turns));
	const threads = mergeKeyed(byId(base.threads), byId(mine.threads), byId(theirs.threads), (before, ours, their) =>
		mergedThread(before, ours, their, turnIds)
	);
	return {
		...theirs,
		threads: [...threads.values()],
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
			turns: Math.max(mine.issued.turns, theirs.issued.turns, turnIds.issued)
		},
		told: furtherByRun(mine.told, theirs.told)
	};
}
