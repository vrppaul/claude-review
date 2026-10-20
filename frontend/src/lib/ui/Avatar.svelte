<script lang="ts">
	import type { Speaker } from './avatar';
	import Icon from './Icon.svelte';
	import type { IconName } from './icons';

	interface Props {
		speaker: Speaker;
	}

	let { speaker }: Props = $props();

	/** How each is drawn: the glyph it stands by, and its class in the library's stylesheet. */
	interface Drawn {
		icon: IconName;
		look: string;
	}

	const DRAWN_AS: Record<Speaker, Drawn> = {
		reader: { icon: 'person', look: 'cr-ui-avatar-reader' },
		agent: { icon: 'story', look: 'cr-ui-avatar-agent' },
		unsaid: { icon: 'person', look: 'cr-ui-avatar-unsaid' }
	};

	const drawn = $derived(DRAWN_AS[speaker]);
</script>

<!-- Who says a turn, round (lib/ui/avatar.ts): as wide as its turn's first column (Turn), which lays out round it -->
<span class={['cr-ui-avatar', drawn.look]}><Icon name={drawn.icon} size="xs" /></span>
