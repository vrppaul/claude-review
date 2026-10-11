import { describe, it, expect } from 'vitest';
import { fileToken, mentionBeingTyped, withMention, withoutThread } from '$lib/anchors/mentions';
import { anchorToken } from '$lib/anchors/views';
import type { Thread } from '$lib/types';
import { newComment } from './new-comment';

/** A thread on lines of a file, as the panel points at one. */
function threadOn(file: string, line: number): Thread {
	const { anchor, body, severity, images } = newComment({ file, startLine: line });
	return { id: 'c1', anchor, body, severity, images, turns: [], raised_by: 'reader', resolved: false, round: 1, at: 0 };
}

describe('a mention being typed', () => {
	it('is what follows an @ up to the caret', () => {
		expect(mentionBeingTyped({ text: 'Look at @src/ro', caret: 15 })).toBe('src/ro');
	});

	it('has just begun at a bare @', () => {
		expect(mentionBeingTyped({ text: 'Look at @', caret: 9 })).toBe('');
	});

	it('is over once a space is typed after it', () => {
		expect(mentionBeingTyped({ text: 'Look at @src and', caret: 16 })).toBeNull();
	});

	it('is read up to the caret, not to the end of the message', () => {
		expect(mentionBeingTyped({ text: 'Look at @src again', caret: 12 })).toBe('src');
	});
});

describe('putting a token in a message', () => {
	it('takes the place of the mention being typed, with a space to go on after', () => {
		expect(withMention({ text: 'Look at @rou', caret: 12 }, '@src/routes.py:2-2')).toEqual({
			text: 'Look at @src/routes.py:2-2 ',
			caret: 27
		});
	});

	it('goes in at the caret when nothing is being typed after an @', () => {
		expect(withMention({ text: 'Look at  please', caret: 8 }, fileToken('a.py'))).toEqual({
			text: 'Look at @a.py  please',
			caret: 14
		});
	});

	it('keeps what was written after the caret', () => {
		expect(withMention({ text: '@a and the rest', caret: 2 }, '@a.py').text).toBe('@a.py  and the rest');
	});
});

describe('taking a thread out of a message', () => {
	it('drops its token like a word, leaving no double space', () => {
		const thread = threadOn('src/routes.py', 2);

		expect(withoutThread(`Look at ${anchorToken(thread.anchor)} again`, thread)).toBe('Look at again');
	});
});
