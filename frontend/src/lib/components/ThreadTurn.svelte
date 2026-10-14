<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { TurnAuthor } from '$lib/types';
	import { AGENT, READER } from '$lib/utils/speakers';
	import Icon from './Icon.svelte';
	import type { IconName } from './icons';

	/** Who a turn is drawn as: whoever said it, or the reader about to say something in the field to reply in. */
	type Voice = TurnAuthor | 'reply';

	/** How a voice is drawn: the name its turns are headed with, if they have a head, its avatar's icon, and its look. */
	interface Speaker {
		name: string | null;
		icon: IconName;
		look: string;
	}

	const SPEAKERS: Record<Voice, Speaker> = {
		[READER]: { name: 'You', icon: 'person', look: 'cr-turn-reader' },
		[AGENT]: { name: 'Agent', icon: 'story', look: 'cr-turn-agent' },
		reply: { name: null, icon: 'person', look: 'cr-turn-reply' }
	};

	interface Props {
		voice: Voice;
		testId: string;
		/** The name the tour lights it by, where the tour points at it. */
		tour?: string | undefined;
		/** Whether it has just landed: an answer nobody has looked at yet, which arrives in the agent's colour. */
		landing?: boolean;
		/** What its head says after who said it: how long ago, and whatever else it says of the turn. */
		head?: Snippet;
		/** What was said, or the field to say it in. */
		children: Snippet;
	}

	let { voice, testId, tour, landing = false, head, children }: Props = $props();

	const speaker = $derived(SPEAKERS[voice]);
</script>

<!-- One turn of a thread: the avatar of who says it, beside their name, the rest of the head and what they
	said. The row draws its own piece of the spine that joins the avatars down the card -->
<div
	data-testid={testId}
	data-tour={tour}
	class={['cr-thread-row cr-thread-turn', speaker.look, landing && 'cr-answer-new']}
>
	<span class="cr-avatar"><Icon name={speaker.icon} /></span>
	<div class="cr-turn-body">
		{#if speaker.name !== null}
			<div class="cr-turn-head">
				<strong class="cr-turn-name">{speaker.name}</strong>
				{@render head?.()}
			</div>
		{/if}
		{@render children()}
	</div>
</div>
