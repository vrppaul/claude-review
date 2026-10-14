<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import { useReview } from '$lib/review/context';
	import type { StoryWait } from '$lib/review/story-wait';
	import Icon from './Icon.svelte';
	import type { IconName } from './icons';
	import StorySketch from './StorySketch.svelte';
	import { factsOnTheWay, type WaitFact } from './story-wait-facts';

	interface Props {
		/** What the reader is waiting on, there being no story to draw. */
		wait: StoryWait;
	}

	/** How a fact is drawn, by whether it has happened: its mark, and the class that colours its mark and its time. */
	interface Drawing {
		mark: IconName;
		class: string;
	}

	// A tick for what is done; a ring of dashes for what is waited for, which is the agent's to do
	const DRAWN_AS: Record<WaitFact['state'], Drawing> = {
		happened: { mark: 'check', class: 'cr-wait-fact-happened' },
		awaited: { mark: 'awaited', class: 'cr-wait-fact-awaited' }
	};

	let { wait }: Props = $props();
	const review = useReview();

	// Everything drawn of the wait, and the control of it that takes the keyboard: each kind of wait says which
	let drawn: HTMLElement | undefined = $state();
	let takesKeyboard: HTMLElement | undefined = $state();

	// The wait changes under the reader — stopped, asked for again, the agent gone — and the control
	// that held the keyboard goes with what was drawn. Looked at before the page redraws: the keyboard
	// then goes to what the wait now draws for it, and is never left on nothing
	$effect.pre(() => {
		// Looked at again whenever the wait changes kind
		void wait.kind;
		if (drawn?.contains(document.activeElement)) focusWhatRemains(() => takesKeyboard);
	});
</script>

<!-- Where the story will be, while there is none: what the reader is waiting on, said as facts, and what
	they can do meanwhile. Said to a screen reader as it changes -->
<section bind:this={drawn} data-testid="story-waiting" role="status" class="cr-story-waiting">
	{#if wait.kind === 'nobody-attached'}
		<div class="flex flex-col items-center gap-3 text-center">
			<p>No story for this review. A story is told by the agent that made the change, and no agent is attached.</p>
			<p class="cr-muted">
				Attach one with <code class="font-mono text-base-content">/review-ui</code> in that session; the story starts as soon
				as it joins.
			</p>
			{@render readFilesMeanwhile()}
		</div>
	{:else if wait.kind === 'stopped'}
		<div class="flex flex-col items-center gap-3 text-center">
			<p>The story was not finished: you stopped it.</p>
			<div class="flex flex-wrap items-center justify-center gap-3">
				<button
					bind:this={takesKeyboard}
					type="button"
					data-testid="write-story-again"
					class="btn btn-primary btn-sm"
					onclick={() => review.story.askFor()}
				>
					Write it again
				</button>
				<span class="cr-muted">or read the files</span>
			</div>
		</div>
	{:else}
		<!-- What is left is a story on its way: its request not landed yet, or being written -->
		<StorySketch waiting />
		<div class="flex flex-col gap-2 text-center">
			<h1 class="text-xl font-semibold">The agent is writing the story</h1>
			<p class="cr-muted">
				It reads the whole change and writes the overview and the chapters in one go. A big change takes a few minutes.
			</p>
		</div>
		<ul data-testid="story-wait-facts" class="cr-wait-facts">
			{#each factsOnTheWay(wait, review.clock) as fact (fact.says)}
				<li data-testid="story-wait-fact" class={['cr-wait-fact', DRAWN_AS[fact.state].class]}>
					<Icon name={DRAWN_AS[fact.state].mark} class="cr-wait-mark" />
					<span>{fact.says}</span>
					<!-- A count that moves every second is read when asked for, never read out as it moves -->
					<span data-testid="story-wait-when" class="cr-wait-when" aria-live="off">{fact.when}</span>
				</li>
			{/each}
		</ul>
		<div class="flex flex-wrap justify-center gap-2.5">
			{@render readFilesMeanwhile()}
			{#if wait.kind === 'writing'}
				<button
					type="button"
					data-testid="stop-writing"
					class="btn btn-ghost btn-sm"
					onclick={() => review.story.stop()}
				>
					Stop writing
				</button>
			{/if}
		</div>
	{/if}
</section>

<!-- The way to the files while the story is not there: offered wherever one is still awaited, and the
	control that takes the keyboard there -->
{#snippet readFilesMeanwhile()}
	<button
		bind:this={takesKeyboard}
		type="button"
		data-testid="read-files-meanwhile"
		class="btn btn-sm"
		onclick={() => review.views.showFiles()}
	>
		Read the files meanwhile
	</button>
{/snippet}
