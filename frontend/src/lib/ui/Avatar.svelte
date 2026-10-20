<script lang="ts">
	import type { AvatarTone } from './avatar';
	import Icon from './Icon.svelte';
	import type { IconName } from './icons';

	interface Props {
		tone: AvatarTone;
	}

	let { tone }: Props = $props();

	/** How each is drawn: the glyph it stands by, and its class in the library's stylesheet. */
	interface Drawn {
		icon: IconName;
		look: string;
	}

	const TONES: Record<AvatarTone, Drawn> = {
		reader: { icon: 'person', look: 'cr-ui-avatar-reader' },
		agent: { icon: 'story', look: 'cr-ui-avatar-agent' },
		unsaid: { icon: 'person', look: 'cr-ui-avatar-unsaid' }
	};

	const drawn = $derived(TONES[tone]);
</script>

<!-- Who says a turn, round (lib/ui/avatar.ts): as wide as the room it stands in, which lays out round it -->
<span class={['cr-ui-avatar', drawn.look]}><Icon name={drawn.icon} size="xs" /></span>
