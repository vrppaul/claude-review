/**
 * Moments said the way a reader says them: how long ago, and at what time.
 *
 * One way to say each, so a thread, the panel and the list of bases never
 * disagree about what the same few minutes are called.
 */

const MILLISECONDS_IN_A_SECOND = 1000;
const SECONDS_IN_A_MINUTE = 60;
const SECONDS_IN_AN_HOUR = 3600;
const SECONDS_IN_A_DAY = 86_400;

/** A unit a span of time is said in, and the letter it is said with. */
interface TimeUnit {
	seconds: number;
	letter: string;
}

// The smallest unit, which a span shorter than any whole unit is said in too: "0s ago"
const SECONDS: TimeUnit = { seconds: 1, letter: 's' };
// The largest first: a span is said in the largest unit it holds a whole one of
const UNITS: readonly TimeUnit[] = [
	{ seconds: SECONDS_IN_A_DAY, letter: 'd' },
	{ seconds: SECONDS_IN_AN_HOUR, letter: 'h' },
	{ seconds: SECONDS_IN_A_MINUTE, letter: 'm' },
	SECONDS
];

// A turn is read, not audited: its time is said to the minute
const TO_THE_MINUTE: Intl.DateTimeFormatOptions = { hour: '2-digit', minute: '2-digit' };

/**
 * How long ago a moment was, in whole units of the largest that fits:
 * "12s ago", "3m ago", "2h ago", "1d ago". A moment a clock a little behind
 * puts in the future was a moment ago.
 */
export function timeAgo(at: number, now: number): string {
	const seconds = Math.max(0, Math.floor((now - at) / MILLISECONDS_IN_A_SECOND));
	const unit = UNITS.find((candidate) => seconds >= candidate.seconds) ?? SECONDS;
	return `${Math.floor(seconds / unit.seconds)}${unit.letter} ago`;
}

/** The time of day a moment was, to the minute. */
export function clockTime(at: number): string {
	return new Date(at).toLocaleTimeString([], TO_THE_MINUTE);
}
