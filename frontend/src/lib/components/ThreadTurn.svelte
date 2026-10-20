<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { TurnAuthor } from '$lib/types';
	import { tourStop, type TourTarget } from '$lib/guide/tour';
	import Avatar from '$lib/ui/Avatar.svelte';
	import type { AvatarTone } from '$lib/ui/avatar';
	import { AGENT, READER } from '$lib/utils/speakers';

	/** Who a turn is drawn as: whoever said it, or the reader about to say something in the field to reply in. */
	type Voice = TurnAuthor | 'reply';

	/** How a voice is drawn: the name its turns are headed with, if they have a head, and its avatar. */
	interface Speaker {
		name: string | null;
		avatar: AvatarTone;
		/** The class of its row, where its turns look their own: the agent's, named in its colour. */
		look: string | null;
	}

	const SPEAKERS: Record<Voice, Speaker> = {
		[READER]: { name: 'You', avatar: 'reader', look: null },
		[AGENT]: { name: 'Agent', avatar: 'agent', look: 'cr-turn-agent' },
		reply: { name: null, avatar: 'unsaid', look: null }
	};

	interface Props {
		voice: Voice;
		testId: string;
		/** The name the tour lights it by, where the tour points at it. */
		tour?: TourTarget | undefined;
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
	data-tour={tour && tourStop(tour)}
	class={['cr-thread-row cr-thread-turn', speaker.look, landing && 'cr-answer-new']}
>
	<Avatar tone={speaker.avatar} />
	<div data-testid="turn-body" class="cr-turn-body">
		{#if speaker.name !== null}
			<div data-testid="turn-head" class="cr-turn-head">
				<strong class="cr-turn-name">{speaker.name}</strong>
				{@render head?.()}
			</div>
		{/if}
		{@render children()}
	</div>
</div>
