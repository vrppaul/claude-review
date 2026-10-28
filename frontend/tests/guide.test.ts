import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import fastCheck from 'fast-check';
import { tick } from 'svelte';
import Guide from '$lib/components/Guide.svelte';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import NewsIllustration from '$lib/components/NewsIllustration.svelte';
import { RELEASE_NEWS, type ReleaseNews } from '$lib/guide/news';
import { isNewer, latestNews, unseenNews } from '$lib/guide/news-choice';
import { writeSeenRelease } from '$lib/guide/seen-release';
import { contextLine, diffFile, hunk } from './diff';
import { said } from './elements';
import { fakeServer, SERVER_ERROR } from './fake-server';
import { guideServer, guideServerIntroduced, guideServerIntroducingFeedback } from './guide-server';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from './review';
import { settled } from './settled';

let review: Review;

// The release whose news introduces Story
const STORY_RELEASE = '1.6.0';
// The release a reader was last shown, and the act of the card they meet that takes the keyboard: the welcome for
// somebody who has never opened a review, the news of 1.5.0 for somebody who last saw 1.4.2
const CARDS_TAKING_THE_KEYBOARD = [
	{ seen: null, mainAct: 'guide-start' },
	{ seen: '1.4.2', mainAct: 'guide-got-it' }
];

beforeEach(() => {
	review = openReview();
});

/** Open a review served by this release, and let the guide decide what to show the reader. */
async function arriveAt(release: string): Promise<void> {
	review = openReview({ facts: { release } });
	await review.guide.open();
}

function entry(release: string, also: string[] = []): ReleaseNews {
	return { release, title: `In ${release}`, body: 'Something new.', also };
}

// What a release number is made of here: up to four parts, and perhaps what it leads up to
const MOST_PARTS = 4;
const LARGEST_PART = 20;
const LEADS_UP_TO = ['', 'rc1', '.dev0'];
const release = fastCheck
	.tuple(
		fastCheck.array(fastCheck.nat({ max: LARGEST_PART }), { minLength: 1, maxLength: MOST_PARTS }),
		fastCheck.constantFrom(...LEADS_UP_TO)
	)
	.map(([parts, suffix]) => `${parts.join('.')}${suffix}`);

describe('which release a reader has seen', () => {
	it('compares releases number by number', () => {
		expect(isNewer('1.10.0', '1.9.3')).toBe(true);
		expect(isNewer('1.5.0', '1.5.0')).toBe(false);
		expect(isNewer('1.4.2', '1.5.0')).toBe(false);
		expect(isNewer('2.0', '1.99.99')).toBe(true);
	});

	it('counts a pre-release as the release it leads up to', () => {
		fastCheck.assert(
			fastCheck.property(release, fastCheck.constantFrom(...LEADS_UP_TO), (numbered, suffix) => {
				expect(isNewer(`${numbered}${suffix}`, numbered)).toBe(false);
				expect(isNewer(numbered, `${numbered}${suffix}`)).toBe(false);
			})
		);
	});

	it('is kept by the server, for every review on the machine', async () => {
		guideServer(null);

		await writeSeenRelease('1.5.0');
		await arriveAt('1.5.0');

		expect(review.guide.card).toBeNull();
	});

	it('takes over the cookie an older release kept it in, once', async () => {
		document.cookie = 'claude-review-seen=1.4.2; path=/';
		const server = guideServer(null);

		await review.guide.open();

		expect(server.bodiesSentTo('PUT /api/guide')).toContainEqual({ seen_release: '1.4.2' });
		expect(document.cookie).not.toContain('claude-review-seen');
		expect(review.guide.card).not.toBe('welcome');
	});
});

describe('which news a returning reader is shown', () => {
	const entries = [entry('1.3.0'), entry('1.4.0'), entry('1.5.0')];

	it('is only the newest one they have not seen', () => {
		expect(unseenNews(entries, '1.2.0', '1.5.0')?.release).toBe('1.5.0');
	});

	it('is the newest one they skipped, when the serving release has none', () => {
		expect(unseenNews(entries, '1.3.0', '1.4.5')?.release).toBe('1.4.0');
	});

	it('is nothing, when nothing was written since they last looked', () => {
		expect(unseenNews(entries, '1.5.0', '1.5.2')).toBeUndefined();
	});

	it('never runs ahead of the release that is serving', () => {
		expect(latestNews(entries, '1.4.9')?.release).toBe('1.4.0');
	});

	it('is written for releases in order, each once', () => {
		const releases = RELEASE_NEWS.map((news) => news.release);
		expect(new Set(releases).size).toBe(releases.length);
		expect(releases.every((release, index) => index === 0 || isNewer(release, releases[index - 1]))).toBe(true);
	});
});

describe('what the guide shows a reader arriving', () => {
	it('welcomes somebody who has never opened a review', async () => {
		guideServer(null);

		await arriveAt('1.5.0');

		expect(review.guide.card).toBe('welcome');
	});

	it('tells somebody back from an older release what changed', async () => {
		guideServer('1.4.2');

		await arriveAt('1.5.0');

		expect(review.guide.card).toBe('news');
		expect(review.guide.news?.release).toBe('1.5.0');
	});

	it('says nothing about a release with nothing written since, and remembers it', async () => {
		const server = guideServer('1.5.0');

		await arriveAt('1.5.1');

		expect(review.guide.card).toBeNull();
		await vi.waitFor(() => expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ seen_release: '1.5.1' }]));
	});

	it('puts the card away for good once it is closed', async () => {
		const server = guideServer(null);
		await arriveAt('1.5.0');

		review.guide.dismiss();

		expect(review.guide.card).toBeNull();
		await vi.waitFor(() => expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ seen_release: '1.5.0' }]));
	});

	it('shows nothing rather than welcome somebody twice when the server cannot say', async () => {
		fakeServer().refuse('GET /api/guide', SERVER_ERROR);

		await arriveAt('1.5.0');

		expect(review.guide.card).toBeNull();
	});

	it('heads the welcome as every pane is headed: what it asks, and the way to put it away', async () => {
		guideServer(null);
		await arriveAt('1.5.0');
		const { getByTestId } = render(Guide, inReview(review));
		await tick();
		const heading = getByTestId('guide-welcome-heading').textContent;

		getByTestId('guide-welcome-close').click();

		expect(heading).toBe('First time here?');
		expect(review.guide.card).toBeNull();
	});

	it('gives the keyboard to the act the welcome or the news leads to, as either appears', async () => {
		const tookIt = [];
		for (const card of CARDS_TAKING_THE_KEYBOARD) {
			guideServer(card.seen);
			await arriveAt('1.5.0');
			const { unmount } = render(Guide, inReview(review));
			await tick();
			tookIt.push(document.activeElement?.getAttribute('data-testid'));
			unmount();
		}

		expect(tookIt).toEqual(CARDS_TAKING_THE_KEYBOARD.map((card) => card.mainAct));
	});

	it('heads the news as every pane is headed: what is new, and the way to put it away', async () => {
		guideServer('1.4.2');
		await arriveAt('1.5.0');
		const { getByTestId } = render(Guide, inReview(review));
		await tick();
		const heading = getByTestId('guide-news-heading').textContent;
		const title = review.guide.news?.title;

		getByTestId('guide-news-close').click();

		expect(heading).toBe(title);
		expect(review.guide.card).toBeNull();
	});
});

describe('Story introduced at the switch', () => {
	it('waits while a newcomer is welcomed', async () => {
		guideServer(null);

		await arriveAt('1.5.0');

		expect(review.guide.introducesStory).toBe(false);
	});

	it('is introduced to a newcomer once the welcome is put away', async () => {
		guideServer(null);
		await arriveAt('1.5.0');

		review.guide.dismiss();

		expect(review.guide.introducesStory).toBe(true);
	});

	it('waits while the tour runs', async () => {
		guideServer(null);
		await arriveAt('1.5.0');

		review.guide.startTour();

		expect(review.guide.introducesStory).toBe(false);
	});

	it('is introduced to a newcomer once the tour ends', async () => {
		guideServer(null);
		await arriveAt('1.5.0');
		review.guide.startTour();

		review.guide.endTour();

		expect(review.guide.introducesStory).toBe(true);
	});

	it('is introduced by the tour once it stops at Story: nothing follows the tour, here or in a later review', async () => {
		const server = guideServer(null);
		await arriveAt('1.5.0');
		review.guide.startTour();
		review.guide.seeTargets(new Set(['story-switch']));

		review.guide.endTour();

		expect(review.guide.introducesStory).toBe(false);
		await vi.waitFor(() => expect(server.bodiesSentTo('PUT /api/guide')).toContainEqual({ story_introduced: true }));
	});

	it('is introduced at once to a returning reader with no news to read', async () => {
		guideServer('1.5.0');

		await arriveAt('1.5.0');

		expect(review.guide.introducesStory).toBe(true);
	});

	it('is introduced at the switch once the news of a release before stories is put away', async () => {
		guideServer('1.4.2');
		await arriveAt('1.5.0');

		review.guide.dismiss();

		expect(review.guide.introducesStory).toBe(true);
	});

	it('is introduced by the news of the release that brought it: nothing follows the card at the switch', async () => {
		guideServer('1.5.0');
		await arriveAt(STORY_RELEASE);

		review.guide.dismiss();

		expect(review.guide.introducesStory).toBe(false);
	});

	it('is kept as done once the news of the release that brought it is shown', async () => {
		const server = guideServer('1.5.0');

		await arriveAt(STORY_RELEASE);

		await vi.waitFor(() => expect(server.bodiesSentTo('PUT /api/guide')).toContainEqual({ story_introduced: true }));
	});

	it('is kept as done once that news is read again from the ? list', async () => {
		const server = guideServer(STORY_RELEASE);
		await arriveAt(STORY_RELEASE);

		review.guide.showNews();

		await vi.waitFor(() => expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ story_introduced: true }]));
	});

	it('is never introduced to a reader it was introduced to', async () => {
		guideServerIntroduced('1.5.0');

		await arriveAt('1.5.0');

		expect(review.guide.introducesStory).toBe(false);
	});

	it('is introduced to no one when the server cannot say: better not introduced than introduced twice', async () => {
		fakeServer().refuse('GET /api/guide', SERVER_ERROR);

		await arriveAt('1.5.0');

		expect(review.guide.introducesStory).toBe(false);
	});

	it('says in the panel which introduction could not be kept, where the server refuses to keep it', async () => {
		const server = guideServer('1.5.0');
		await arriveAt('1.5.0');
		server.refuse('PUT /api/guide', SERVER_ERROR, 'the review fell over');

		review.guide.noteStoryIntroduced();
		review.guide.noteFeedbackIntroduced();

		await vi.waitFor(() =>
			expect(review.conversation.turns.slice(-2).map((turn) => turn.body)).toEqual([
				'whether Story is introduced again could not be kept — the review fell over',
				'whether Send feedback is introduced again could not be kept — the review fell over'
			])
		);
	});

	it('is kept as done where the reader is introduced before the server says, and is not introduced once it does', async () => {
		const server = guideServer('1.5.0');
		review = openReview({ facts: { release: '1.5.0' } });

		review.guide.noteStoryIntroduced();
		await review.guide.open();

		expect(review.guide.introducesStory).toBe(false);
		await vi.waitFor(() => expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ story_introduced: true }]));
	});

	it('is kept as done once, however often the reader is introduced', async () => {
		const server = guideServer('1.5.0');
		await arriveAt('1.5.0');

		review.guide.noteStoryIntroduced();
		review.guide.noteStoryIntroduced();

		await vi.waitFor(() => expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ story_introduced: true }]));
	});
});

describe('Send feedback introduced under Help', () => {
	it('is introduced to a returning reader Story was introduced to before', async () => {
		guideServerIntroducingFeedback('1.5.0');

		await arriveAt('1.5.0');

		expect(review.guide.introducesFeedback).toBe(true);
	});

	it('waits for a review of its own where Story is introduced, even once Story is put away for good', async () => {
		guideServer('1.5.0');
		await arriveAt('1.5.0');
		const whileStoryIs = review.guide.introducesFeedback;

		review.guide.noteStoryIntroduced();

		expect([whileStoryIs, review.guide.introducesFeedback]).toEqual([false, false]);
	});

	it('waits while the news, the tour or Help stands over the review', async () => {
		guideServerIntroducingFeedback('1.5.0');
		await arriveAt('1.5.0');

		review.guide.showNews();
		const underTheNews = review.guide.introducesFeedback;
		review.guide.startTour();
		const underTheTour = review.guide.introducesFeedback;
		review.guide.endTour();
		review.guide.setHelpOpen(true);
		const underHelp = review.guide.introducesFeedback;

		expect([underTheNews, underTheTour, underHelp]).toEqual([false, false, false]);
	});

	it('is kept as done once the reader opens Send feedback, and is not introduced again', async () => {
		const server = guideServerIntroducingFeedback('1.5.0');
		await arriveAt('1.5.0');

		review.guide.showFeedback();
		review.guide.closeFeedback();

		expect(review.guide.introducesFeedback).toBe(false);
		await vi.waitFor(() => expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ feedback_introduced: true }]));
	});

	it('is introduced in a review that tells no story, where Story is not, though it was never introduced', async () => {
		guideServer('1.5.0');
		review = openReview({ facts: { release: '1.5.0', takes_a_story: false } });

		await review.guide.open();

		expect([review.guide.introducesStory, review.guide.introducesFeedback]).toEqual([false, true]);
	});
});

describe('the news card', () => {
	it('links to the release on GitHub even when there is nothing else to list', async () => {
		guideServer('1.4.2');
		await arriveAt('1.5.0');

		const { getByTestId } = render(Guide, inReview(review));
		await tick();

		expect(getByTestId('guide-release-link').getAttribute('href')).toBe(
			'https://github.com/vrppaul/claude-review/releases/tag/v1.5.0'
		);
	});

	it('says the release it is news of beside its heading', async () => {
		guideServer('1.4.2');
		await arriveAt('1.5.0');

		const { getByTestId } = render(Guide, inReview(review));
		await tick();

		expect(getByTestId('guide-release').textContent).toBe('1.5.0');
	});

	it('shows a picture from a file, described for whoever cannot see it', () => {
		const { getByTestId } = render(
			NewsIllustration,
			inReview(review, { illustration: { kind: 'image', src: '/news/paste.gif', alt: 'A screenshot pasted' } })
		);

		const image = getByTestId('news-image') as HTMLImageElement;
		expect(image.getAttribute('src')).toBe('/news/paste.gif');
		expect(image.alt).toBe('A screenshot pasted');
	});

	it('tells of Story in the release that brought it', async () => {
		guideServer('1.5.0');
		await arriveAt(STORY_RELEASE);

		const { getByTestId } = render(Guide, inReview(review));
		await tick();

		expect(said(getByTestId('guide-news'))).toContain('Read a change as a story');
	});

	it('tells, a line each, what else the release that brought Story changed', async () => {
		guideServer('1.5.0');
		await arriveAt(STORY_RELEASE);

		const { getByTestId } = render(Guide, inReview(review));
		await tick();

		const told = said(getByTestId('guide-news'));
		expect(told).toContain(
			'A new look: the header says which repository and branch you review, Send counts what goes with it, and both side columns can be put away to a rail.'
		);
		expect(told).toContain(
			'Edit or delete your comment or reply until the agent has read it, and take back a question you asked.'
		);
		expect(told).toContain('A comment you are writing is never lost: a reload brings it back as it was.');
		expect(told).toContain('The page says when the review cannot be reached, and catches up once it is back.');
	});

	it('offers Try Story in place of Got it for the release that brought Story', async () => {
		guideServer('1.5.0');
		await arriveAt(STORY_RELEASE);

		const { getByTestId, queryByTestId } = render(Guide, inReview(review));
		await tick();

		expect(said(getByTestId('guide-try-story'))).toBe('Try Story');
		expect(queryByTestId('guide-got-it')).toBeNull();
	});

	it('offers Got it, and no Try Story, for any other release', async () => {
		guideServer('1.4.2');
		await arriveAt('1.5.0');

		const { getByTestId, queryByTestId } = render(Guide, inReview(review));
		await tick();

		expect(getByTestId('guide-got-it')).toBeTruthy();
		expect(queryByTestId('guide-try-story')).toBeNull();
	});

	it('offers Got it in a review that tells no story: Try Story would lead to a view it does not have', async () => {
		guideServer('1.5.0');
		review = openReview({ facts: { release: STORY_RELEASE, takes_a_story: false } });
		await review.guide.open();

		const { getByTestId, queryByTestId } = render(Guide, inReview(review));
		await tick();

		expect(getByTestId('guide-got-it')).toBeTruthy();
		expect(queryByTestId('guide-try-story')).toBeNull();
	});

	it('puts the card away by Try Story and asks before stories are turned on, as Story in the header does', async () => {
		guideServer('1.5.0');
		review = openReview({ facts: { release: STORY_RELEASE } });
		await review.guide.open();
		const { getByTestId, queryByTestId } = render(ReviewScreen, { props: { review } });
		await tick();

		getByTestId('guide-try-story').click();
		await tick();

		expect(queryByTestId('guide-news')).toBeNull();
		expect(getByTestId('story-opt-in')).toBeTruthy();
	});

	it('leaves the keyboard on Story once the question its Try Story asked is put away: the card is gone', async () => {
		guideServer('1.5.0');
		review = openReview({ facts: { release: STORY_RELEASE } });
		await review.guide.open();
		const { getByTestId } = render(ReviewScreen, { props: { review } });
		await tick();
		getByTestId('guide-try-story').click();
		await tick();

		getByTestId('stories-not-now').click();
		await tick();
		await tick();

		expect(document.activeElement?.getAttribute('data-testid')).toBe('read-as-story');
	});

	it('draws a story sketched, for an entry that names it', () => {
		const { getByTestId } = render(
			NewsIllustration,
			inReview(review, { illustration: { kind: 'drawing', name: 'story-sketch' } })
		);

		expect(getByTestId('story-sketch')).toBeTruthy();
	});
});

describe('the ? list', () => {
	it('opens from a button too, for whoever has ? taken by a browser extension', async () => {
		const opened = openReview({ files: [diffFile({ path: 'a.py', hunks: [hunk([contextLine(1, 1, 'x')])] })] });
		const { getByTestId, queryByTestId } = render(ReviewScreen, { props: { review: opened } });
		expect(queryByTestId('shortcuts-list')).toBeNull();

		getByTestId('open-help').click();
		await tick();

		expect(getByTestId('shortcuts-list')).toBeTruthy();
	});

	it('thanks the reader in place of the ask once they follow Star, with the keyboard on the thanks', async () => {
		const opened = openReview({ files: [diffFile({ path: 'a.py', hunks: [hunk([contextLine(1, 1, 'x')])] })] });
		const { getByTestId, queryByTestId } = render(ReviewScreen, { props: { review: opened } });
		getByTestId('open-help').click();
		await tick();
		getByTestId('star-on-github').focus();

		getByTestId('star-on-github').click();
		await settled();

		expect(queryByTestId('star-on-github')).toBeNull();
		expect(document.activeElement).toBe(getByTestId('star-on-github-thanks'));
	});

	it('asks again the next time Help opens: whether the reader starred it, the page cannot know', async () => {
		const opened = openReview({ files: [diffFile({ path: 'a.py', hunks: [hunk([contextLine(1, 1, 'x')])] })] });
		const { getByTestId, queryByTestId } = render(ReviewScreen, { props: { review: opened } });
		getByTestId('open-help').click();
		await tick();
		getByTestId('star-on-github').click();
		await tick();

		getByTestId('open-help').click();
		await tick();
		getByTestId('open-help').click();
		await tick();

		expect([queryByTestId('star-on-github-thanks'), getByTestId('star-on-github')]).toEqual([null, expect.anything()]);
	});
});
