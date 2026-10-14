/** A review opened the way the page opens one, for a test to read and draw. */
import { flushSync } from 'svelte';
import { pageAsScrollArea, type ScrollArea } from '$lib/dom/scroll-area';
import { PageLayout } from '$lib/reader/page-layout.svelte';
import { PageTheme } from '$lib/reader/page-theme.svelte';
import { ReplySound } from '$lib/reader/reply-sound';
import { Settings } from '$lib/reader/settings.svelte';
import { reviewContext } from '$lib/review/context';
import type { Review } from '$lib/review/review.svelte';
import type {
	DiffFile,
	DiffResponse,
	HeldThread,
	ReviewResponse,
	SaidInPanel,
	StoryAsking,
	StoryHeld
} from '$lib/types';
import { openKeptReview, type KeptReview } from '$lib/page/kept-review';
import { diffResponse, reviewResponse } from './diff';
import { NEW_READER, type FakeServer } from './fake-server';

/** What a test says about the review it opens; the rest is a diff in its first round. */
export interface Opened {
	files?: DiffFile[];
	/** What the server says the review is. */
	facts?: Partial<ReviewResponse>;
	/** The first diff, beyond its files. */
	diff?: Partial<DiffResponse>;
	/** The reader's settings, where a test reads them. */
	settings?: Settings;
	/** The threads the review holds, which a review opening with no draft takes in. */
	held?: HeldThread[];
	/** What the review holds of the panel, which a review opens on whatever its draft holds. */
	said?: SaidInPanel[];
	/** The story the review holds, if the agent told one. */
	story?: StoryHeld | null;
	/** How the reader's asking for a story stands, if they asked for one. */
	asking?: StoryAsking | null;
}

/** What the review says of itself with an agent attached: the panel then offers its field, and a story asked for is written. */
export const AGENT_ATTACHED: Partial<ReviewResponse> = { answerer_attached: true };

// The page open in this tab: the review it holds, keeping its draft as the page does
let openPage: KeptReview | null = null;

/**
 * Let the page open in this tab go, as a reload or a closed tab does: what
 * it was about to keep is kept first.
 */
export function leavePage(): void {
	// What the page changed last is noticed before it goes, as in a browser
	flushSync();
	openPage?.stopKeeping();
	openPage = null;
}

/**
 * Open a review as the page does: from what the server says it is, its
 * first diff, and whatever unsent draft of the same review this browser
 * kept — and keep its draft from then on. Opening another is a reload: the
 * page before it goes first.
 */
export function openReview({
	files = [],
	facts,
	diff,
	settings = new Settings(),
	held = [],
	said = [],
	story = null,
	asking = null
}: Opened = {}): Review {
	leavePage();
	openPage = openKeptReview(
		{
			facts: reviewResponse(facts),
			firstDiff: diffResponse({ files, ...diff }),
			held,
			said,
			story: { held: story, asking }
		},
		{ settings, layout: new PageLayout(), sound: new ReplySound(settings), theme: new PageTheme(settings) }
	);
	return openPage.review;
}

/** The settings of a reader who turned stories on in some review, as a page that read them from this server holds them. */
export async function settingsWithStoriesOn(server: FakeServer): Promise<Settings> {
	server.answer('GET /api/settings', { record: { ...NEW_READER, stories: true }, stored: true });
	const settings = new Settings();
	await settings.load();
	return settings;
}

/** What a component drawn on its own is handed down: the review, and how to read the area it scrolls in. */
type HandedDown = Map<symbol, Review | ScrollArea>;

/**
 * The options a component drawn on its own needs to be drawn inside this
 * review: the review, and the page itself as the area it scrolls in.
 */
export function inReview(review: Review): { context: HandedDown };
export function inReview<Props>(review: Review, props: Props): { props: Props; context: HandedDown };
export function inReview<Props>(review: Review, props?: Props) {
	const context: HandedDown = new Map([...reviewContext(review), ...pageAsScrollArea()]);
	return props === undefined ? { context } : { props, context };
}
