<script lang="ts">
	import { focusWhatCarries, focusWhatRemains } from '$lib/dom/keyboard';
	import { releaseUrl } from '$lib/guide/news';
	import { useReview } from '$lib/review/context';
	import Actions from '$lib/ui/Actions.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Dot from '$lib/ui/Dot.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Key from '$lib/ui/Key.svelte';
	import Link from '$lib/ui/Link.svelte';
	import Pane from '$lib/ui/Pane.svelte';
	import Tag from '$lib/ui/Tag.svelte';
	import NewsIllustration from './NewsIllustration.svelte';
	import { HELP_BUTTON_ROLE } from './keymap';

	// What the welcome asks a newcomer, which heads it; and what each card's cross says it does
	const WELCOME = 'First time here?';
	const CLOSE_THE_WELCOME = 'Close the welcome';
	const CLOSE_THE_NEWS = 'Close the news';

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

	let title = $state<HTMLElement>();
	let mainAction = $state<HTMLButtonElement>();

	// A card that appears offers the act it leads to, unless the reader is busy:
	// it takes the keyboard from no one — not from a comment the tour asked for
	$effect(() => {
		if (review.guide.card !== null) focusWhatRemains(() => mainAction);
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
	<div class="cr-guide-place">
		<Pane width="medium" testId="guide-tour" aria-label="Tour of the review">
			<div class="cr-guide-card">
				<div class="flex items-center gap-2">
					<div class="flex gap-1" aria-hidden="true">
						{#each stepNumbers as index (index)}
							<span class={['cr-guide-tick', index <= review.guide.stepPosition && 'cr-guide-tick-done']}></span>
						{/each}
					</div>
					<span class="cr-faint text-xs">{review.guide.stepPosition + 1} of {review.guide.stepCount}</span>
					<span class="flex-1"></span>
					<span class="text-xs">
						<Link testId="guide-skip" onclick={skipTour}>Skip tour</Link>
					</span>
				</div>
				<!-- What a screen reader is told at each step: the words, not the controls -->
				<div class="flex flex-col gap-3" aria-live="polite">
					<!-- The step's title heads the card as a pane's heading does, but is the step's own, said anew as the
						step changes and given the keyboard when nothing else holds it, so no head of a pane draws it -->
					<Heading tag="h2" heads="pane" bind:element={title} tabindex={-1}>{step.title}</Heading>
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
						<Dot tone="reader" testId="guide-waiting-dot" />
						{waiting.hint}
					</p>
				{/if}
				<Actions testId="guide-step-actions">
					{#snippet others()}
						{#if review.guide.canGoBack}
							<Button tone="quiet" size="sm" testId="guide-back" onclick={() => review.guide.back()}>Back</Button>
						{/if}
					{/snippet}
					{#snippet main()}
						{#if !waiting}
							<Button tone="primary" size="sm" testId="guide-next" onclick={goOn}>
								{review.guide.isLastStep ? 'Done' : 'Next'}
							</Button>
						{/if}
					{/snippet}
				</Actions>
			</div>
		</Pane>
	</div>
{:else if review.guide.card === 'welcome'}
	<div class="cr-guide-place">
		<Pane
			width="medium"
			testId="guide-welcome"
			role="complementary"
			aria-label={WELCOME}
			head={{ heading: WELCOME, close: putAway, closing: CLOSE_THE_WELCOME }}
		>
			<div class="cr-guide-card">
				<div class="flex items-start gap-3">
					<Icon name="compass" size="xl" tone="reader" />
					<p class="cr-guide-body">
						A short walk through one review: what you are reading, where comments go, and how the agent answers them. {review
							.guide.stepCount} stops, about two minutes.
					</p>
				</div>
				<Actions testId="guide-welcome-actions">
					{#snippet others()}
						<Button tone="quiet" size="sm" testId="guide-not-now" onclick={putAway}>Not now</Button>
					{/snippet}
					{#snippet main()}
						<Button
							bind:element={mainAction}
							tone="primary"
							size="sm"
							testId="guide-start"
							onclick={() => review.guide.startTour()}
						>
							Show me around
						</Button>
					{/snippet}
				</Actions>
				<p class="cr-faint text-xs">
					You can take it later from the <Key keys="?" stands="inline" testId="guide-help-key" /> list.
				</p>
			</div>
		</Pane>
	</div>
{:else if review.guide.card === 'news' && news}
	<div class="cr-guide-place">
		<!-- The release it is new in, beside what is new -->
		{#snippet newIn()}
			<span class="cr-faint text-xs">New in</span>
			<Tag tone="quiet" testId="guide-release">{news.release}</Tag>
		{/snippet}
		<Pane
			width="medium"
			testId="guide-news"
			role="complementary"
			aria-label={news.title}
			head={{ heading: news.title, close: putAway, closing: CLOSE_THE_NEWS, aside: newIn }}
		>
			<div class="cr-guide-card">
				{#if news.illustration}
					<NewsIllustration illustration={news.illustration} />
				{/if}
				<p class="cr-guide-body">{news.body}</p>
				{#if news.also.length > 0}
					<div class="flex flex-col gap-1.5 border-t border-base-300 pt-3">
						<span class="cr-faint text-xs">Also in this release</span>
						{#each news.also as line (line)}
							<span class="cr-guide-body">{line}</span>
						{/each}
					</div>
				{/if}
				<p class="cr-guide-body">
					<Link testId="guide-release-link" href={releaseUrl(news.release)}
						>Everything in {news.release}, on GitHub</Link
					>
				</p>
				<Actions testId="guide-news-actions">
					{#snippet others()}
						<Button tone="quiet" size="sm" testId="guide-take-tour" onclick={() => review.guide.startTour()}>
							Take the tour
						</Button>
					{/snippet}
					{#snippet main()}
						{#if offersStory}
							<Button bind:element={mainAction} tone="primary" size="sm" testId="guide-try-story" onclick={tryStory}>
								Try Story
							</Button>
						{:else}
							<Button bind:element={mainAction} tone="primary" size="sm" testId="guide-got-it" onclick={putAway}>
								Got it
							</Button>
						{/if}
					{/snippet}
				</Actions>
			</div>
		</Pane>
	</div>
{/if}
