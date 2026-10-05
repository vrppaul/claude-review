import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { render } from '@testing-library/svelte';
import { tick } from 'svelte';
import Guide from '$lib/components/Guide.svelte';
import KeyboardShortcuts from '$lib/components/KeyboardShortcuts.svelte';
import TopBar from '$lib/components/TopBar.svelte';
import NewsIllustration from '$lib/components/NewsIllustration.svelte';
import { RELEASE_NEWS, type ReleaseNews } from '$lib/guide/news';
import { latestNews, unseenNews } from '$lib/guide/news-choice';
import { TOUR_STEPS } from '$lib/guide/tour';
import { guideStore } from '$lib/stores/guide.svelte';
import { commentFields } from '$lib/stores/comment-fields';
import { reviewStore } from '$lib/stores/review.svelte';
import { isNewer, readSeenRelease, writeSeenRelease } from '$lib/utils/seen-release';

// Every component's source, to check the tour points only at places that exist
const SOURCES = import.meta.glob('../src/**/*.svelte', {
	query: '?raw',
	import: 'default',
	eager: true
}) as Record<string, string>;

function forgetCookie() {
	document.cookie = 'claude-review-seen=; path=/; max-age=0';
}

function entry(release: string, also: string[] = []): ReleaseNews {
	return { release, title: `In ${release}`, body: 'Something new.', also };
}

/** A page on which exactly these places are drawn. */
function pageWith(...names: string[]) {
	guideStore.readPageWith((targets) => targets.some((target) => names.includes(target)));
}

describe('which release a reader has seen', () => {
	afterEach(forgetCookie);

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

	it('remembers it in a cookie, which every port of 127.0.0.1 shares', () => {
		expect(readSeenRelease()).toBeNull();
		writeSeenRelease('1.5.0');
		expect(readSeenRelease()).toBe('1.5.0');
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
		expect(releases.every((release, index) => index === 0 || isNewer(release, releases[index - 1]))).toBe(
			true
		);
	});
});

describe('what the guide shows a reader arriving', () => {
	beforeEach(() => {
		forgetCookie();
		guideStore.clear();
	});

	it('welcomes somebody who has never opened a review', () => {
		guideStore.open('1.5.0');

		expect(guideStore.card).toBe('welcome');
	});

	it('tells somebody back from an older release what changed', () => {
		writeSeenRelease('1.4.2');

		guideStore.open('1.5.0');

		expect(guideStore.card).toBe('news');
		expect(guideStore.news?.release).toBe('1.5.0');
	});

	it('says nothing about a release with nothing written since, and remembers it', () => {
		writeSeenRelease('1.5.0');

		guideStore.open('1.5.1');

		expect(guideStore.card).toBeNull();
		expect(readSeenRelease()).toBe('1.5.1');
	});

	it('puts the card away for good once it is closed', () => {
		guideStore.open('1.5.0');

		guideStore.dismiss();

		expect(guideStore.card).toBeNull();
		expect(readSeenRelease()).toBe('1.5.0');
	});
});

describe('the news card', () => {
	beforeEach(() => {
		forgetCookie();
		guideStore.clear();
	});

	it('links to the release on GitHub even when there is nothing else to list', async () => {
		writeSeenRelease('1.4.2');
		guideStore.open('1.5.0');

		const { getByTestId } = render(Guide);
		await tick();

		expect(getByTestId('guide-release-link').getAttribute('href')).toBe(
			'https://github.com/vrppaul/claude-review/releases/tag/v1.5.0'
		);
	});

	it('shows a picture from a file, described for whoever cannot see it', () => {
		const { getByTestId } = render(NewsIllustration, {
			props: { illustration: { kind: 'image', src: '/news/paste.gif', alt: 'A screenshot pasted' } }
		});

		const image = getByTestId('news-image') as HTMLImageElement;
		expect(image.getAttribute('src')).toBe('/news/paste.gif');
		expect(image.alt).toBe('A screenshot pasted');
	});
});

describe('the tour', () => {
	beforeEach(() => {
		forgetCookie();
		guideStore.clear();
		reviewStore.clear();
	});

	afterEach(() => {
		guideStore.endTour();
	});

	it('points only at places the review actually marks', () => {
		const everywhere = Object.values(SOURCES).join('\n');
		for (const name of TOUR_STEPS.flatMap((step) => step.targets)) {
			expect(everywhere, name).toMatch(new RegExp(`data-tour=(?:"${name}"|\\{[^}]*'${name}'[^}]*\\})`));
		}
	});

	it('takes the steps a review with an agent has, and leaves out the others', () => {
		reviewStore.attachAnswerer();
		guideStore.startTour();
		const seen: string[] = [];
		while (guideStore.step) {
			seen.push(guideStore.step.id);
			guideStore.next();
		}

		expect(seen).toContain('comment-route');
		expect(seen).toContain('round-or-end');
		expect(seen).not.toContain('comment-save');
		expect(seen).not.toContain('finish');
	});

	it('passes over a step with nothing on screen to show', () => {
		// A plan under review has no base to choose: the tour opens on the files
		pageWith('file-tree', 'line-number');

		guideStore.startTour();

		expect(guideStore.step?.id).toBe('files');
	});

	it('turns round at the start rather than landing on a step with nothing to show', () => {
		pageWith('file-tree', 'line-number');
		guideStore.startTour();

		guideStore.back();

		expect(guideStore.step?.id).toBe('files');
	});

	it('waits for a comment on a line, not for a reply', () => {
		pageWith('file-tree', 'line-number', 'comment-field');
		guideStore.startTour();
		guideStore.next();
		expect(guideStore.step?.id).toBe('comment-line');

		guideStore.notice({ type: 'opened', kind: 'reply' });
		expect(guideStore.step?.id).toBe('comment-line');

		guideStore.notice({ type: 'opened', kind: 'new' });
		expect(guideStore.step?.id).toBe('comment-save');
	});

	it('does not wait for a comment that is already open', () => {
		pageWith('file-tree', 'line-number', 'comment-field');
		guideStore.notice({ type: 'opened', kind: 'new' });

		guideStore.startTour();
		guideStore.next();

		expect(guideStore.step?.id).toBe('comment-save');
	});

	it('follows the comment where the reader sent it', () => {
		reviewStore.attachAnswerer();
		pageWith('file-tree', 'line-number', 'comment-field', 'awaited-answer', 'unsent-count');
		guideStore.startTour();
		guideStore.next();
		guideStore.notice({ type: 'opened', kind: 'new' });
		expect(guideStore.step?.id).toBe('comment-route');

		guideStore.notice({ type: 'asked', kind: 'new' });

		expect(guideStore.step?.id).toBe('asked');
	});

	it('goes back a step when the comment is closed without being sent', () => {
		reviewStore.attachAnswerer();
		pageWith('file-tree', 'line-number', 'comment-field');
		guideStore.startTour();
		guideStore.next();
		guideStore.notice({ type: 'opened', kind: 'new' });

		guideStore.notice({ type: 'closed', kind: 'new' });

		expect(guideStore.step?.id).toBe('comment-line');
	});

	it('leaves Escape to whatever is open over the review', async () => {
		pageWith('review-base');
		guideStore.startTour();
		render(Guide);
		await tick();

		window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));

		expect(guideStore.touring).toBe(true);
	});

	it('keeps waiting for a comment while another one on a line is still open', () => {
		reviewStore.attachAnswerer();
		pageWith('file-tree', 'line-number', 'comment-field');
		guideStore.startTour();
		guideStore.next();
		guideStore.notice({ type: 'opened', kind: 'new' });
		guideStore.notice({ type: 'opened', kind: 'new' });

		guideStore.notice({ type: 'closed', kind: 'new' });

		expect(guideStore.step?.id).toBe('comment-route');
	});

	it('counts only the steps it will show, and offers no Back before the first', () => {
		pageWith('file-tree', 'line-number');
		guideStore.startTour();

		expect(guideStore.stepPosition).toBe(0);
		expect(guideStore.canGoBack).toBe(false);
		expect(guideStore.stepCount).toBe(2);
	});

	it('hears the comment fields once the page shows what happened', async () => {
		pageWith('file-tree', 'line-number', 'comment-field');
		guideStore.startTour();
		render(Guide);
		await tick();
		guideStore.readPageWith((targets) =>
			targets.some((target) => ['file-tree', 'line-number', 'comment-field'].includes(target))
		);
		guideStore.next();

		commentFields.report({ type: 'opened', kind: 'new' });
		expect(guideStore.step?.id).toBe('comment-line');
		await tick();

		expect(guideStore.step?.id).toBe('comment-save');
	});
});

describe('the ? list', () => {
	beforeEach(() => {
		guideStore.clear();
	});

	it('opens from a button too, for whoever has ? taken by a browser extension', async () => {
		const { getByTestId, queryByTestId } = render(KeyboardShortcuts);
		const { getByTestId: inHeader } = render(TopBar, {
			props: { submitting: false, error: null, onOpenModal: () => {} }
		});
		expect(queryByTestId('shortcuts-list')).toBeNull();

		inHeader('open-help').click();
		await tick();

		expect(getByTestId('shortcuts-list')).toBeTruthy();
	});
});
