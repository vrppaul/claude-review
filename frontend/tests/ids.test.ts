import { describe, it, expect } from 'vitest';
import { IdSequence } from '$lib/utils/ids';

describe('ids the browser hands out', () => {
	it('are short and readable, one after another', () => {
		const comments = new IdSequence('comment-');

		expect([comments.next(), comments.next()]).toEqual(['comment-1', 'comment-2']);
	});

	it('carry on past the highest of their kind that a restored draft holds', () => {
		const comments = new IdSequence('comment-');

		comments.continuePast(['comment-3', 'comment-1', 'raised-9', 'turn-7', undefined]);

		expect(comments.next()).toBe('comment-4');
	});

	it('pass over an id of their kind that carries no number', () => {
		const comments = new IdSequence('comment-');

		comments.continuePast(['comment-', 'comment-x', 'comment-2']);

		expect(comments.next()).toBe('comment-3');
	});
});
