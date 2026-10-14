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
import { fakeServer, SERVER_ERROR } from './fake-server';
import { guideServer, guideServerIntroduced } from './guide-server';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from './review';

let review: Review;

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

	it('counts a pre-release or a development build as the release it leads to', () => {
		expect(isNewer('1.5.0rc1', '1.5.0')).toBe(false);
		expect(isNewer('1.4.3.dev0', '1.4.2')).toBe(true);
	});

	it('orders releases as an order does: none after itself, never both ways round, and on through a third', () => {
		fastCheck.assert(
			fastCheck.property(release, release, release, (first, second, third) => {
				expect(isNewer(first, first)).toBe(false);
				if (isNewer(first, second)) expect(isNewer(second, first)).toBe(false);
				if (isNewer(first, second) && isNewer(second, third)) expect(isNewer(first, third)).toBe(true);
			})
		);
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

	it('is introduced at once to a returning reader with no news to read', async () => {
		guideServer('1.5.0');

		await arriveAt('1.5.0');

		expect(review.guide.introducesStory).toBe(true);
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

	it('is put away for this page alone by its cross, and nothing is kept', async () => {
		const server = guideServer('1.5.0');
		await arriveAt('1.5.0');

		review.guide.putIntroductionAway();

		expect(review.guide.introducesStory).toBe(false);
		expect(server.bodiesSentTo('PUT /api/guide')).toEqual([]);
	});

	it('is kept as done once the reader is introduced, for every review', async () => {
		const server = guideServer('1.5.0');
		await arriveAt('1.5.0');

		review.guide.noteStoryIntroduced();

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

	it('comes back where the reader undoes having it put away for good, and is kept as not done', async () => {
		const server = guideServer('1.5.0');
		await arriveAt('1.5.0');
		review.guide.noteStoryIntroduced();

		review.guide.introduceStoryAgain();

		expect(review.guide.introducesStory).toBe(true);
		await vi.waitFor(() =>
			expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ story_introduced: true }, { story_introduced: false }])
		);
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

	it('shows a picture from a file, described for whoever cannot see it', () => {
		const { getByTestId } = render(
			NewsIllustration,
			inReview(review, { illustration: { kind: 'image', src: '/news/paste.gif', alt: 'A screenshot pasted' } })
		);

		const image = getByTestId('news-image') as HTMLImageElement;
		expect(image.getAttribute('src')).toBe('/news/paste.gif');
		expect(image.alt).toBe('A screenshot pasted');
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
});
