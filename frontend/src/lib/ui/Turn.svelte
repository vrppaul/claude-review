<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import Avatar from './Avatar.svelte';
	import type { AvatarTone } from './avatar';

	/** How a speaker's turns are headed: the name, where they have a head, and the class of the row, where it looks its own. */
	interface Heading {
		name: string | null;
		look: string | null;
	}

	// The agent's name is said in its colour; the reader about to say something has no head yet
	const HEADINGS: Record<AvatarTone, Heading> = {
		reader: { name: 'You', look: null },
		agent: { name: 'Agent', look: 'cr-ui-turn-agent' },
		unsaid: { name: null, look: null }
	};

	interface Props extends Omit<HTMLAttributes<HTMLDivElement>, 'class' | 'style' | 'children'> {
		/** Who says it: the reader, the agent, or the reader about to say something in the field it holds. */
		speaker: AvatarTone;
		testId: string;
		/** Whether it has just landed: an answer nobody has looked at yet, which arrives in the agent's colour. */
		landing?: boolean;
		/** What its head says after who said it: how long ago, and whatever else it says of the turn. */
		head?: Snippet | undefined;
		/** What was said, or the field to say it in. */
		children: Snippet;
	}

	let { speaker, testId, landing = false, head, children, ...attributes }: Props = $props();

	const heading = $derived(HEADINGS[speaker]);
</script>

<!-- One turn of a conversation, a thread's or the panel's: the avatar of who says it, beside their name, the
	rest of the head and what they said. The row draws its own piece of the spine that joins the avatars down
	the conversation (Conversation) -->
<div
	{...attributes}
	data-testid={testId}
	class={['cr-ui-turn-row cr-ui-turn', heading.look, landing && 'cr-ui-turn-landing']}
>
	<Avatar tone={speaker} />
	<div data-testid="turn-body" class="cr-ui-turn-body">
		{#if heading.name !== null}
			<div data-testid="turn-head" class="cr-ui-turn-head">
				<strong class="cr-ui-turn-name">{heading.name}</strong>
				{@render head?.()}
			</div>
		{/if}
		{@render children()}
	</div>
</div>
