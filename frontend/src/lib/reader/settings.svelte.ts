/**
 * How this reader reads a review, kept by the server for every review.
 *
 * Every review runs on a port of its own and the browser keeps one storage
 * per port, so a choice kept there was gone in the next repository's review.
 * The server keeps it in the reader's configuration instead.
 *
 * The theme is cached in this port's storage as well: the page applies it
 * before its first paint, long before the server could answer.
 */

import { keepSettings, readSettings } from '$lib/api/review-api';
import type { DiffLayout, ReaderSettings, Theme } from '$lib/types';
import { forget, readChoice, readFlag, writeChoice } from '$lib/utils/preferences';

/** What a reader who has never chosen anything gets. */
const NEW_READER: ReaderSettings = {
	theme: 'system',
	diff_layout: 'unified',
	ignore_whitespace: false,
	sound_on_replies: false,
	story_writing: 'ask_first'
};

/** The choices this browser kept before the server did: these four, and none added since. */
type KeptHere = Pick<ReaderSettings, 'theme' | 'diff_layout' | 'ignore_whitespace' | 'sound_on_replies'>;

const THEMES: readonly Theme[] = ['system', 'light', 'dark'];
const LAYOUTS: readonly DiffLayout[] = ['unified', 'split'];

// The names this browser kept choices under before the server kept them.
// The theme's stays: it is the cache the first paint reads, in index.html.
const THEME_CACHE = 'theme';
const LAYOUT_KEPT_HERE = 'layout';
const WHITESPACE_KEPT_HERE = 'ignore-whitespace';
const SOUND_KEPT_HERE = 'reply-sound';

/** What this browser kept before the server did, read under the old names. */
function keptInThisBrowser(): KeptHere {
	return {
		theme: readChoice(THEME_CACHE, THEMES, NEW_READER.theme),
		diff_layout: readChoice(LAYOUT_KEPT_HERE, LAYOUTS, NEW_READER.diff_layout),
		ignore_whitespace: readFlag(WHITESPACE_KEPT_HERE, NEW_READER.ignore_whitespace),
		sound_on_replies: readFlag(SOUND_KEPT_HERE, NEW_READER.sound_on_replies)
	};
}

/** Whether this browser kept any choice a new reader would not have. */
function choseAnything(kept: KeptHere): boolean {
	return (
		kept.theme !== NEW_READER.theme ||
		kept.diff_layout !== NEW_READER.diff_layout ||
		kept.ignore_whitespace !== NEW_READER.ignore_whitespace ||
		kept.sound_on_replies !== NEW_READER.sound_on_replies
	);
}

/** The reader's settings: here at once, and on the server for every later review. */
export class Settings {
	#current = $state.raw<ReaderSettings>({
		...NEW_READER,
		theme: readChoice(THEME_CACHE, THEMES, NEW_READER.theme)
	});

	get current(): ReaderSettings {
		return this.#current;
	}

	/**
	 * Read what the reader chose, in this review or any other.
	 *
	 * A reader the server has nothing on may still have choices this browser
	 * kept before the server did: they are handed over once, and the old
	 * copies dropped, so no other port hands over its stale ones later.
	 */
	async load(): Promise<void> {
		try {
			const kept = await readSettings();
			const local = keptInThisBrowser();
			this.#current = kept.stored || !choseAnything(local) ? kept.record : await keepSettings(local);
			forget(LAYOUT_KEPT_HERE);
			forget(WHITESPACE_KEPT_HERE);
			forget(SOUND_KEPT_HERE);
			writeChoice(THEME_CACHE, this.#current.theme);
		} catch {
			// A server that cannot say leaves this tab reading as it was
		}
	}

	/**
	 * Read again what the reader chose: another tab, of this review or any
	 * other, may have changed it since. The choices alone: what this browser
	 * kept before the server did was handed over as the page opened. A read
	 * that fails throws, and leaves the settings as they were.
	 */
	async readAgain(): Promise<void> {
		this.#current = (await readSettings()).record;
		writeChoice(THEME_CACHE, this.#current.theme);
	}

	/** Make a choice, here at once and for every later review once the server has it. */
	async change(changes: Partial<ReaderSettings>): Promise<void> {
		this.#current = { ...this.#current, ...changes };
		writeChoice(THEME_CACHE, this.#current.theme);
		try {
			await keepSettings(changes);
		} catch {
			// The choice still applies to this tab, it just will not be remembered
		}
	}
}
