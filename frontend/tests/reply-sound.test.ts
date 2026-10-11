import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import { ReplySound } from '$lib/reader/reply-sound';
import { Settings } from '$lib/reader/settings.svelte';
import { fakeServer, keepingSettings } from './fake-server';

// Longer than answers handed over together take to arrive, in milliseconds
const A_WHILE_LATER = 2000;

/** A part of a sound — a tone, a level — connected, started and stopped, making nothing. */
class SilentPart {
	readonly frequency = { value: 0 };
	readonly gain = { setValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() };
	type = '';
	onended: (() => void) | null = null;
	readonly start = vi.fn();
	readonly stop = vi.fn();

	connect(next: SilentPart): SilentPart {
		return next;
	}
}

/** A sound card that counts the ticks it is asked to play — the tones started — and plays none. */
class CountingSound {
	static played = 0;
	readonly currentTime = 0;
	readonly destination = new SilentPart();
	readonly close = vi.fn();

	createOscillator(): SilentPart {
		const tone = new SilentPart();
		tone.start.mockImplementation(() => {
			CountingSound.played += 1;
		});
		return tone;
	}

	createGain(): SilentPart {
		return new SilentPart();
	}
}

/** The tick, for a reader who asked to hear answers. */
async function heardAnswers(): Promise<ReplySound> {
	keepingSettings(fakeServer());
	const settings = new Settings();
	await settings.change({ sound_on_replies: true });
	return new ReplySound(settings);
}

describe('the tick an answer makes', () => {
	beforeEach(() => {
		CountingSound.played = 0;
		vi.stubGlobal('AudioContext', CountingSound);
		// Only a review in a background tab ticks
		vi.spyOn(document, 'hidden', 'get').mockReturnValue(true);
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.unstubAllGlobals();
	});

	it('ticks once for answers handed over together', async () => {
		const sound = await heardAnswers();

		sound.announce();
		sound.announce();
		sound.announce();

		expect(CountingSound.played).toBe(1);
	});

	it('ticks again for an answer that comes a while later', async () => {
		const sound = await heardAnswers();

		sound.announce();
		vi.advanceTimersByTime(A_WHILE_LATER);
		sound.announce();

		expect(CountingSound.played).toBe(2);
	});

	it('leaves a browser with no sound at all reading on', async () => {
		vi.stubGlobal('AudioContext', undefined);
		const sound = await heardAnswers();

		expect(() => sound.announce()).not.toThrow();
	});
});
