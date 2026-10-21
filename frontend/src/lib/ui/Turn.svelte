<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import Avatar from './Avatar.svelte';
	import { VOICE_NAMES, type Voice } from './voice';

	// Each speaker's row's class, where it has its own: the agent's name is said in its colour
	const LOOKS: Record<Voice, string | null> = { reader: null, agent: 'cr-ui-turn-agent' };

	interface Props extends Omit<HTMLAttributes<HTMLDivElement>, 'class' | 'style' | 'children'> {
		/** Who says it: the reader or the agent. */
		speaker: Voice;
		testId: string;
		/** Whether it has just landed: an answer nobody has looked at yet, which arrives in the agent's colour. */
		landing?: boolean;
		/** Whether the reader took back what it says: still read, its words struck through (TakenBack says so under it). */
		takenBack?: boolean;
		/** What its head says after who said it: how long ago, and whatever else it says of the turn. */
		head?: Snippet | undefined;
		/** What stands at the far end of its head: what can be done to the turn, or how long it has been waited on. */
		headEnd?: Snippet | undefined;
		/** What was said, or the field it is rewritten in. */
		children: Snippet;
	}

	let { speaker, testId, landing = false, takenBack = false, head, headEnd, children, ...attributes }: Props = $props();
</script>

<!-- One turn of a conversation, a thread's or the panel's: the avatar of who says it, beside their name, the
	rest of the head, its far end, and what they said. The row draws its own piece of the spine that joins the
	avatars down the conversation (Conversation) -->
<div
	{...attributes}
	data-testid={testId}
	class={[
		'cr-ui-turn-row cr-ui-turn',
		LOOKS[speaker],
		landing && 'cr-ui-turn-landing',
		takenBack && 'cr-ui-turn-taken-back'
	]}
>
	<Avatar {speaker} />
	<div data-testid="turn-body" class="cr-ui-turn-body">
		<div data-testid="turn-head" class="cr-ui-turn-head">
			<strong class="cr-ui-turn-name">{VOICE_NAMES[speaker]}</strong>
			{@render head?.()}
			{#if headEnd}
				<div data-testid="turn-head-end" class="cr-ui-turn-head-end">{@render headEnd()}</div>
			{/if}
		</div>
		{@render children()}
	</div>
</div>
