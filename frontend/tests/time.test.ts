import { describe, it, expect } from 'vitest';
import { clockTimeToTheSecond, timeAgo, timeWaited } from '$lib/utils/time';

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

describe('the time of day a moment was, to the second', () => {
	it('says its minutes and its seconds, each in two digits', () => {
		// Ten seconds past four minutes past one in the afternoon, wherever the tests are run
		const moment = new Date(2026, 9, 14, 13, 4, 10).getTime();

		expect(clockTimeToTheSecond(moment)).toContain(':04:10');
	});
});

describe('how long something has been waited for, as a stopwatch says it', () => {
	it('counts seconds in two digits under a minute', () => {
		expect(timeWaited(NOW - 8 * SECOND, NOW)).toBe('0:08');
		expect(timeWaited(NOW - 48 * SECOND, NOW)).toBe('0:48');
	});

	it('counts whole minutes before the seconds left over', () => {
		expect(timeWaited(NOW - (3 * MINUTE + 5 * SECOND), NOW)).toBe('3:05');
	});

	it('goes on counting minutes past an hour', () => {
		expect(timeWaited(NOW - (HOUR + MINUTE + SECOND), NOW)).toBe('61:01');
	});

	it('says no time has passed for a moment a clock a little behind puts in the future', () => {
		expect(timeWaited(NOW + 5 * SECOND, NOW)).toBe('0:00');
	});
});
