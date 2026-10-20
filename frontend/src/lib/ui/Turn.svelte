<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import Avatar from './Avatar.svelte';
	import type { Speaker } from './avatar';

	/** How a speaker's turns are headed: their name, where they have a head, and their row's class, if its own. */
	interface Headed {
		name: string | null;
		look: string | null;
	}

	// The agent's name is said in its colour; the reader about to say something has no head yet
	const HEADED: Record<Speaker, Headed> = {
		reader: { name: 'You', look: null },
		agent: { name: 'Agent', look: 'cr-ui-turn-agent' },
		unsaid: { name: null, look: null }
	};

	interface Props extends Omit<HTMLAttributes<HTMLDivElement>, 'class' | 'style' | 'children'> {
		/** Who says it: the reader, the agent, or the reader about to say something in the field it holds. */
		speaker: Speaker;
		testId: string;
		/** Whether it has just landed: an answer nobody has looked at yet, which arrives in the agent's colour. */
		landing?: boolean;
		/** What its head says after who said it: how long ago, and whatever else it says of the turn. */
		head?: Snippet | undefined;
		/** What stands at the far end of its head: what can be done to the turn, or how long it has been waited on. */
		headEnd?: Snippet | undefined;
		/** What was said, or the field to say it in. */
		children: Snippet;
	}

	let { speaker, testId, landing = false, head, headEnd, children, ...attributes }: Props = $props();

	const headed = $derived(HEADED[speaker]);
</script>

<!-- One turn of a conversation, a thread's or the panel's: the avatar of who says it, beside their name, the
	rest of the head, its far end, and what they said. The row draws its own piece of the spine that joins the
	avatars down the conversation (Conversation) -->
<div
	{...attributes}
	data-testid={testId}
	class={['cr-ui-turn-row cr-ui-turn', headed.look, landing && 'cr-ui-turn-landing']}
>
	<Avatar {speaker} />
	<div data-testid="turn-body" class="cr-ui-turn-body">
		{#if headed.name !== null}
			<div data-testid="turn-head" class="cr-ui-turn-head">
				<strong class="cr-ui-turn-name">{headed.name}</strong>
				{@render head?.()}
				{#if headEnd}
					<div data-testid="turn-head-end" class="cr-ui-turn-head-end">{@render headEnd()}</div>
				{/if}
			</div>
		{/if}
		{@render children()}
	</div>
</div>
