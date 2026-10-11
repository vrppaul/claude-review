import { describe, it, expect } from 'vitest';
import { timeAgo } from '$lib/utils/time';

const SECOND = 1000;
const MINUTE = 60 * SECOND;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;
const NOW = 1_000_000_000_000;

describe('how long ago, in the words a conversation uses', () => {
	it('counts seconds under a minute', () => {
		expect(timeAgo(NOW - 12 * SECOND, NOW)).toBe('12s ago');
	});

	it('counts whole minutes under an hour, never sixty of them', () => {
		expect(timeAgo(NOW - 90 * SECOND, NOW)).toBe('1m ago');
		expect(timeAgo(NOW - (HOUR - SECOND), NOW)).toBe('59m ago');
	});

	it('counts whole hours under a day', () => {
		expect(timeAgo(NOW - HOUR, NOW)).toBe('1h ago');
		expect(timeAgo(NOW - (DAY - SECOND), NOW)).toBe('23h ago');
	});

	it('counts days after that', () => {
		expect(timeAgo(NOW - 3 * DAY, NOW)).toBe('3d ago');
	});

	it('says no time has passed for a moment a clock a little behind puts in the future', () => {
		expect(timeAgo(NOW + 5 * SECOND, NOW)).toBe('0s ago');
	});
});
