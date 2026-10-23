<script lang="ts">
	import Icon from './Icon.svelte';
	import type { IconName } from './icons';
	import type { Voice } from './voice';

	interface Props {
		speaker: Voice;
	}

	let { speaker }: Props = $props();

	/** How each is drawn: the glyph it stands by, and its class in the library's stylesheet. */
	interface Drawn {
		icon: IconName;
		look: string;
	}

	const DRAWN_AS: Record<Voice, Drawn> = {
		reader: { icon: 'person', look: 'cr-ui-avatar-reader' },
		agent: { icon: 'story', look: 'cr-ui-avatar-agent' }
	};

	const drawn = $derived(DRAWN_AS[speaker]);
</script>

<!-- Who says a turn, round, by their glyph on a ground of their colour: as wide as the room it stands in, which lays
	out round it: its turn's first column (Turn), the mark on a rail of who is behind it (SpeakerMark), or the start of
	the top line of a frame of code (CodeFrameHead, and a band heading one) -->
<span class={['cr-ui-avatar', drawn.look]}><Icon name={drawn.icon} size="xs" /></span>
