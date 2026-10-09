import { afterEach, describe, it, expect, vi } from 'vitest';
import { flushSync } from 'svelte';
import { DraftRepository } from '$lib/drafts/draft-repository';
import { takePush } from '$lib/page/push-handling';
import { storageKey } from '$lib/utils/preferences';
import { newComment } from './new-comment';
import { pushedAt } from './pushes';
import { Tab } from './two-tabs';

const DRAFT_KEY = storageKey('draft');
const TITLE = 'repo: uncommitted changes';
// Another run of the review than the one most tabs here read
const ANOTHER_RUN = 'another-run';
// How long two tabs that agree are watched for keeping anything more, in milliseconds
const A_WHILE = 5000;
// How far apart two tabs take in the same push, in milliseconds
const TAKEN_APART = 5;
// A thread the agent raised, told to every tab on the review
const POINT = {
	type: 'point',
	thread_id: 'raised-1',
	anchor: newComment().anchor,
	body: 'Look',
	severity: 'note'
} as const;

let tabs: Tab[] = [];

/** A tab opened on the review, from whatever draft the browser keeps as it opens. */
function opened(tab: Tab): Tab {
	tabs.push(tab);
	return tab;
}

function bodies(tab: Tab): string[] {
	return tab.review.threads.all.map((thread) => thread.body);
}

function keptBodies(): string[] {
	return new DraftRepository().load(TITLE)?.threads.map((thread) => thread.body) ?? [];
}

afterEach(() => {
	for (const tab of tabs) tab.close();
	tabs = [];
	vi.useRealTimers();
});

describe('two tabs on one review', () => {
	it("keep each other's threads when both keep at once", () => {
		const tabA = opened(new Tab());
		const tabB = opened(new Tab());
		tabA.review.threads.add(newComment({ body: 'written in A' }));
		tabB.review.threads.add(newComment({ body: 'written in B' }));

		tabA.keep();
		tabB.keep();
		tabA.hearOtherTab();
		tabB.hearOtherTab();

		const both = ['written in A', 'written in B'];
		expect(bodies(tabA)).toEqual(both);
		expect(bodies(tabB)).toEqual(both);
		expect(keptBodies()).toEqual(both);
	});

	it('take in an edit made in the other tab once, however soon after opening', () => {
		const tabA = opened(new Tab());
		const id = tabA.review.threads.add(newComment({ body: 'Why?' }));
		tabA.keep();
		const tabB = opened(new Tab());

		tabA.review.threads.update(id, 'Why, exactly?', 'question', []);
		tabA.keep();
		tabB.hearOtherTab();

		expect(bodies(tabB)).toEqual(['Why, exactly?']);
	});

	it('keep the answer the other tab took in on a thread this tab is changing', () => {
		const tabA = opened(new Tab());
		const id = tabA.review.threads.add(newComment({ body: 'Why?' }));
		tabA.keep();
		const tabB = opened(new Tab());
		tabB.review.threads.receiveReply(id, 'Because.', null, pushedAt(1));
		tabB.keep();

		tabA.review.threads.update(id, 'Why, exactly?', 'question', []);
		tabA.hearOtherTab();
		tabB.hearOtherTab();

		for (const tab of [tabA, tabB]) {
			const [thread] = tab.review.threads.all;
			expect(thread.body).toBe('Why, exactly?');
			expect(thread.turns.map((turn) => turn.body)).toEqual(['Because.']);
		}
	});

	it('keep the answer the other tab took in on a thread this tab left alone', () => {
		const tabA = opened(new Tab());
		const changed = tabA.review.threads.add(newComment({ startLine: 1, body: 'Why?' }));
		const answered = tabA.review.threads.add(newComment({ startLine: 2, body: 'And this?' }));
		tabA.keep();
		const tabB = opened(new Tab());
		tabB.review.threads.receiveReply(answered, 'Because.', null, pushedAt(1));
		tabB.keep();

		tabA.review.threads.update(changed, 'Why, exactly?', 'question', []);
		tabA.hearOtherTab();

		expect(tabA.review.threads.all.map((thread) => [thread.body, thread.turns.length])).toEqual([
			['Why, exactly?', 0],
			['And this?', 1]
		]);
	});

	it('take in what the other tab changed in a thread this tab left alone, as the other tab left it', () => {
		const tabA = opened(new Tab());
		takePush(tabA.review, POINT, pushedAt(1));
		tabA.keep();
		const tabB = opened(new Tab());

		tabB.review.threads.reading.markRead(POINT.thread_id);
		tabB.keep();
		tabA.hearOtherTab();

		expect(tabA.review.threads.unread).toEqual([]);
	});

	it('keep once an answer both tabs took in, a moment apart, on a thread this tab is changing', () => {
		vi.useFakeTimers();
		const tabA = opened(new Tab());
		const id = tabA.review.threads.add(newComment({ body: 'Why?' }));
		tabA.keep();
		const tabB = opened(new Tab());
		tabB.review.threads.receiveReply(id, 'Because.', null, pushedAt(1));
		tabB.keep();
		vi.advanceTimersByTime(TAKEN_APART);

		tabA.review.threads.receiveReply(id, 'Because.', null, pushedAt(1));
		tabA.review.threads.update(id, 'Why, exactly?', 'question', []);
		tabA.hearOtherTab();

		expect(tabA.review.threads.all[0].turns.map((turn) => turn.body)).toEqual(['Because.']);
	});

	it('keep both notes the tabs wrote under one id, and one for a push both took in', () => {
		vi.useFakeTimers();
		const tabA = opened(new Tab());
		const tabB = opened(new Tab());
		tabA.review.conversation.note('noted in A');
		tabB.review.conversation.note('noted in B');
		takePush(tabA.review, POINT, pushedAt(1));
		vi.advanceTimersByTime(TAKEN_APART);
		takePush(tabB.review, POINT, pushedAt(1));

		tabA.keep();
		tabB.keep();

		const panel = new DraftRepository().load(TITLE)?.panel ?? [];
		expect(panel.filter((turn) => turn.body === 'noted in A' || turn.body === 'noted in B')).toHaveLength(2);
		expect(new Set(panel.map((turn) => turn.id)).size).toBe(panel.length);
		expect(panel.filter((turn) => turn.pushedAt !== undefined)).toHaveLength(1);
		expect(keptBodies()).toEqual(['Look']);
	});

	it('leave the kept draft alone once tabs on different runs of the review agree', () => {
		vi.useFakeTimers();
		const tabA = opened(new Tab());
		const tabB = opened(new Tab({ instance: ANOTHER_RUN }));
		takePush(tabA.review, { type: 'progress', work: null }, pushedAt(1));
		takePush(tabB.review, { type: 'progress', work: null }, { instance: ANOTHER_RUN, sequence: 1 });
		tabA.keep();
		tabB.hearOtherTab();
		tabA.hearOtherTab();
		const read = vi.spyOn(Storage.prototype, 'getItem');
		const written = vi.spyOn(Storage.prototype, 'setItem');

		flushSync();
		vi.advanceTimersByTime(A_WHILE);

		expect(read.mock.calls.filter(([key]) => key === DRAFT_KEY)).toEqual([]);
		expect(written.mock.calls.filter(([key]) => key === DRAFT_KEY)).toEqual([]);
	});
});
