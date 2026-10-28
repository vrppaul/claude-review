/**
 * What each release changed, as a reader who last saw an older one is told.
 *
 * Written by hand, one entry per release worth telling about, newest last.
 * A release with no entry says nothing of its own, so a patch that only
 * fixes things stays quiet.
 */

import { REPOSITORY_URL } from '$lib/guide/repository';

/** The drawings an entry can ask for, by name; `NewsIllustration` draws them. */
export type DrawingName = 'pasted-screenshot' | 'story-sketch';

/**
 * A picture above the words. Either a file — a screenshot, or a GIF to show
 * something moving — imported beside the entry so the build carries it; or a
 * small drawing in markup, which follows the theme.
 */
export type Illustration = { kind: 'image'; src: string; alt: string } | { kind: 'drawing'; name: DrawingName };

export interface ReleaseNews {
	release: string;
	title: string;
	body: string;
	/** Smaller changes, a line each. */
	also: string[];
	illustration?: Illustration;
	/** The news is Story's introduction: shown, it introduces Story, and its card offers to try it. */
	introducesStory?: true;
}

const RELEASES_URL = `${REPOSITORY_URL}/releases/tag`;

/** The GitHub release a news entry points to for everything else in it. */
export function releaseUrl(release: string): string {
	return `${RELEASES_URL}/v${release}`;
}

export const RELEASE_NEWS: ReleaseNews[] = [
	{
		release: '1.5.0',
		title: 'Paste a screenshot anywhere you write',
		body: 'Ctrl+V puts an image into the panel, or into any comment, reply or edit. The agent gets it as a file it can open, and an image can be the whole question.',
		also: [
			'A short tour of the review, from the ? list whenever you want it.',
			'The panel waits for the agent to join instead of showing you setup commands.'
		],
		illustration: { kind: 'drawing', name: 'pasted-screenshot' }
	},
	{
		// Seen by no reader until the release brings pyproject to its number
		release: '1.6.0',
		title: 'Read a change as a story',
		body: "The agent can walk you through what it changed: a short overview, then chapters, with its reason above each piece of code. Story asks first, since a story spends the agent's tokens, until you tell it not to.",
		also: [
			'A new look: the header says which repository and branch you review, Send counts what goes with it, and both side columns can be put away to a rail.',
			'Edit or delete your comment or reply until the agent has read it, and take back a question you asked.',
			'A comment you are writing is never lost: a reload brings it back as it was.',
			'The page says when the review cannot be reached, and catches up once it is back.'
		],
		illustration: { kind: 'drawing', name: 'story-sketch' },
		introducesStory: true
	}
];
