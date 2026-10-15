<script lang="ts">
	import type { ClassValue } from 'svelte/elements';
	import Icon from './Icon.svelte';

	interface Props {
		folded: boolean;
		/** How large it is drawn, for the control it sits in. */
		class: ClassValue;
	}

	let { folded, class: size }: Props = $props();
</script>

<!-- One chevron for everything that folds, at the far end of what it folds: pointing down while what it
	folds is away, as pressing it opens that below; up while it is open, as pressing it folds that up -->
<Icon name="chevron" class={[size, 'transition-transform', !folded && 'rotate-180']} />
