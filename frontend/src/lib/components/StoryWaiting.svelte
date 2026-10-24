<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import { useReview } from '$lib/review/context';
	import type { StoryWait } from '$lib/review/story-wait';
	import Actions from '$lib/ui/Actions.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Card from '$lib/ui/Card.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import InlineCode from '$lib/ui/InlineCode.svelte';
	import type { IconName, IconTone } from '$lib/ui/icons';
	import StorySketch from './StorySketch.svelte';
	import { factsOnTheWay, type WaitFact } from './story-wait-facts';
	import { ATTACH_COMMAND, STOP_WRITING, WRITE_IT_AGAIN } from './story-words';

	interface Props {
		/** What the reader is waiting on, there being no story to draw. */
		wait: StoryWait;
	}

	/** How a fact is drawn, by whether it has happened: its mark in its tone, and the class that steps its time back. */
	interface Drawing {
		mark: IconName;
		tone: IconTone;
		class: string | null;
	}

	// A tick for what is done; a ring of dashes for what is waited for, which is the agent's to do
	const DRAWN_AS: Record<WaitFact['state'], Drawing> = {
		happened: { mark: 'check', tone: 'done', class: 'cr-wait-fact-happened' },
		awaited: { mark: 'awaited', tone: 'agent', class: null }
	};

	let { wait }: Props = $props();
	const review = useReview();

	// Everything drawn of the wait, and the control of it that takes the keyboard: each kind of wait says which
	let drawn: HTMLElement | undefined = $state();
	let takesKeyboard: HTMLButtonElement | undefined = $state();

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
				Attach one with <InlineCode code={ATTACH_COMMAND} kind="command" /> in that session; the story starts as soon as it
				joins.
			</p>
			{@render waysOn(false)}
		</div>
	{:else if wait.kind === 'stopped'}
		<div class="flex flex-col items-center gap-3 text-center">
			<p>The story was not finished: you stopped it.</p>
			<Actions testId="story-stopped-actions">
				{#snippet main()}
					<Button
						bind:element={takesKeyboard}
						tone="primary"
						size="sm"
						testId="write-story-again"
						onclick={() => review.story.askFor()}
					>
						{WRITE_IT_AGAIN}
					</Button>
				{/snippet}
			</Actions>
			<p class="cr-muted">or read the files</p>
		</div>
	{:else}
		<!-- What is left is a story on its way: its request not landed yet, or being written -->
		<StorySketch waiting />
		<div class="flex flex-col gap-2 text-center">
			<Heading tag="h1" heads="story">The agent is writing the story</Heading>
			<p class="cr-muted">
				It reads the whole change and writes the overview and the chapters in one go. A big change takes a few minutes.
			</p>
		</div>
		<!-- The facts of it, on a card: a row each -->
		<Card tone="quiet" testId="story-wait-facts">
			<ul class="flex flex-col gap-2">
				{#each factsOnTheWay(wait, review.clock) as fact (fact.says)}
					<li data-testid="story-wait-fact" class={['cr-wait-fact', DRAWN_AS[fact.state].class]}>
						<Icon name={DRAWN_AS[fact.state].mark} size="sm" tone={DRAWN_AS[fact.state].tone} />
						<span>{fact.says}</span>
						<!-- A count that moves every second is read when asked for, never read out as it moves -->
						<span data-testid="story-wait-when" class="cr-wait-when" aria-live="off">{fact.when}</span>
					</li>
				{/each}
			</ul>
		</Card>
		{@render waysOn(wait.kind === 'writing')}
	{/if}
</section>

<!-- What can be done while a story is still awaited, under the words, in the middle of the column: read the
	files meanwhile, the act the wait leads to and the control that takes the keyboard there; and stop the
	writing, while it is being written -->
{#snippet waysOn(stoppable: boolean)}
	<div class="flex justify-center">
		<Actions testId="story-waiting-actions">
			{#snippet others()}
				{#if stoppable}
					<Button tone="quiet" size="sm" testId="stop-writing" onclick={() => review.story.stop()}>
						{STOP_WRITING}
					</Button>
				{/if}
			{/snippet}
			{#snippet main()}
				<Button
					bind:element={takesKeyboard}
					tone="primary"
					size="sm"
					testId="read-files-meanwhile"
					onclick={() => review.views.showFiles()}
				>
					Read the files meanwhile
				</Button>
			{/snippet}
		</Actions>
	</div>
{/snippet}
