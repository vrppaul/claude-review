<script lang="ts">
	import { focusWhatCarries, focusWhatRemains } from '$lib/dom/keyboard';
	import { releaseUrl } from '$lib/guide/news';
	import { useReview } from '$lib/review/context';
	import NewsIllustration from './NewsIllustration.svelte';
	import Icon from './Icon.svelte';
	import { HELP_BUTTON_ROLE } from './keymap';

	const review = useReview();

	const step = $derived(review.guide.step);
	const news = $derived(review.guide.news);
	// What the reader does to move on, when it is not pressing Next
	const waiting = $derived(step?.waitsFor);
	// One mark per step, filled up to the one on screen
	const stepNumbers = $derived([...Array(review.guide.stepCount).keys()]);
	// Whether the news offers to try Story: it is Story's introduction, in a review a story can be told of. In
	// any other it says Got it, and has introduced Story all the same
	const offersStory = $derived(news?.introducesStory === true && review.story.canBeTold);

	let title = $state<HTMLElement | null>(null);
	let firstAction = $state<HTMLButtonElement | null>(null);

	// A card that appears offers its first button, unless the reader is busy:
	// it takes the keyboard from no one — not from a comment the tour asked for
	$effect(() => {
		if (review.guide.card !== null) focusWhatRemains(() => firstAction);
	});

	// A step reached with focus nowhere — the button that led to it is gone —
	// puts it on the title, so the keyboard starts from what the step says
	$effect(() => {
		if (step) focusWhatRemains(() => title);
	});

	/**
	 * The card goes — the tour over, the welcome or the news put away — and
	 * the button pressed with it: the keyboard goes to the help, where the
	 * tour and the news are found again.
	 */
	function keyboardToHelp() {
		focusWhatCarries(HELP_BUTTON_ROLE);
	}

	function skipTour() {
		review.guide.endTour();
		keyboardToHelp();
	}

	/** On to the next step, or out of the tour after its last. */
	function goOn() {
		review.guide.next();
		if (!review.guide.touring) keyboardToHelp();
	}

	function putAway() {
		review.guide.dismiss();
		keyboardToHelp();
	}

	/** Put the news away and read the review as its story, as Story in the header does: asked first where it must be. */
	function tryStory() {
		review.guide.dismiss();
		review.wayIntoStory.readAsStory();
	}
</script>

<!-- One card, bottom left: the welcome, what is new, or the tour talking -->
{#if review.guide.touring && step}
	<section data-testid="guide-tour" class="cr-guide-card" aria-label="Tour of the review">
		<div class="flex items-center gap-2.5">
			<div class="flex gap-1" aria-hidden="true">
				{#each stepNumbers as index (index)}
					<span class={['cr-guide-tick', index <= review.guide.stepPosition && 'cr-guide-tick-done']}></span>
				{/each}
			</div>
			<span class="cr-faint text-xs">{review.guide.stepPosition + 1} of {review.guide.stepCount}</span>
			<span class="flex-1"></span>
			<button type="button" data-testid="guide-skip" class="cr-faint px-0.5 text-xs" onclick={skipTour}>
				Skip tour
			</button>
		</div>
		<!-- What a screen reader is told at each step: the words, not the controls -->
		<div class="flex flex-col gap-3" aria-live="polite">
			<h2 bind:this={title} class="cr-guide-title" tabindex="-1">{step.title}</h2>
			<p class="cr-guide-body">{step.body}</p>
		</div>
		{#if step.fork}
			<ol class="cr-guide-forks">
				{#each step.fork as option (option.label)}
					<li class="cr-guide-fork">
						<span class={['cr-guide-route', option.primary && 'cr-guide-route-primary']}>{option.label}</span>
						<span class="cr-guide-body">{option.says}</span>
					</li>
				{/each}
			</ol>
		{/if}
		{#if waiting}
			<p data-testid="guide-waiting" class="cr-guide-hint">
				<span class="cr-guide-hint-dot"></span>
				{waiting.hint}
			</p>
		{/if}
		<div class="flex items-center gap-2">
			{#if review.guide.canGoBack}
				<button
					type="button"
					data-testid="guide-back"
					class="btn btn-outline btn-sm"
					onclick={() => review.guide.back()}
				>
					Back
				</button>
			{/if}
			<span class="flex-1"></span>
			{#if !waiting}
				<button type="button" data-testid="guide-next" class="btn btn-primary btn-sm" onclick={goOn}>
					{review.guide.isLastStep ? 'Done' : 'Next'}
				</button>
			{/if}
		</div>
	</section>
{:else if review.guide.card === 'welcome'}
	<section data-testid="guide-welcome" class="cr-guide-card" role="complementary" aria-labelledby="guide-welcome-title">
		<div class="flex items-center gap-2.5">
			<Icon name="compass" class="cr-guide-compass" />
			<h2 id="guide-welcome-title" class="cr-guide-title">First time here?</h2>
			<span class="flex-1"></span>
			<button type="button" data-testid="guide-close" class="btn btn-ghost btn-xs" aria-label="Close" onclick={putAway}
				>×</button
			>
		</div>
		<p class="cr-guide-body">
			A short walk through one review: what you are reading, where comments go, and how the agent answers them. {review
				.guide.stepCount} stops, about two minutes.
		</p>
		<div class="flex items-center gap-2">
			<button
				type="button"
				bind:this={firstAction}
				data-testid="guide-start"
				class="btn btn-primary btn-sm"
				onclick={() => review.guide.startTour()}
			>
				Show me around
			</button>
			<button type="button" data-testid="guide-not-now" class="btn btn-ghost btn-sm" onclick={putAway}>
				Not now
			</button>
		</div>
		<p class="cr-faint text-xs">You can take it later from the <kbd class="cr-guide-key">?</kbd> list.</p>
	</section>
{:else if review.guide.card === 'news' && news}
	<section data-testid="guide-news" class="cr-guide-card" role="complementary" aria-labelledby="guide-news-title">
		<div class="flex items-center gap-2">
			<span class="cr-faint text-xs">New in</span>
			<span class="cr-guide-release">{news.release}</span>
			<span class="flex-1"></span>
			<button type="button" data-testid="guide-close" class="btn btn-ghost btn-xs" aria-label="Close" onclick={putAway}
				>×</button
			>
		</div>
		<h2 id="guide-news-title" class="cr-guide-title">{news.title}</h2>
		{#if news.illustration}
			<NewsIllustration illustration={news.illustration} />
		{/if}
		<p class="cr-guide-body">{news.body}</p>
		{#if news.also.length > 0}
			<div class="flex flex-col gap-1.5 border-t border-base-300 pt-2.5">
				<span class="cr-faint text-xs">Also in this release</span>
				{#each news.also as line (line)}
					<span class="cr-guide-body">{line}</span>
				{/each}
			</div>
		{/if}
		<a
			data-testid="guide-release-link"
			class="cr-guide-link"
			href={releaseUrl(news.release)}
			target="_blank"
			rel="noopener noreferrer"
		>
			Everything in {news.release}, on GitHub
		</a>
		<div class="flex items-center gap-2">
			{#if offersStory}
				<button
					type="button"
					bind:this={firstAction}
					data-testid="guide-try-story"
					class="btn btn-primary btn-sm"
					onclick={tryStory}
				>
					Try Story
				</button>
			{:else}
				<button
					type="button"
					bind:this={firstAction}
					data-testid="guide-got-it"
					class="btn btn-primary btn-sm"
					onclick={putAway}
				>
					Got it
				</button>
			{/if}
			<button
				type="button"
				data-testid="guide-take-tour"
				class="btn btn-ghost btn-sm"
				onclick={() => review.guide.startTour()}
			>
				Take the tour
			</button>
		</div>
	</section>
{/if}
