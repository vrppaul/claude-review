<script lang="ts">
	import Icon from './Icon.svelte';
	import type { IconName } from './icons';
	import { TILE_TONES, type TileTone } from './tile';

	interface Props {
		tone: TileTone;
		/** The mark it draws. */
		icon: IconName;
	}

	let { tone, icon }: Props = $props();
</script>

<!-- A mark on its colour's chip, at the start of a card in that colour (lib/ui/tile.ts) -->
<span aria-hidden="true" class={['cr-ui-tile', TILE_TONES[tone]]}><Icon name={icon} size="sm" /></span>
