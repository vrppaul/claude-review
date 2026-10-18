<script lang="ts">
	import type { ClassValue } from 'svelte/elements';
	import Icon from './Icon.svelte';

	interface Props {
		folded: boolean;
		/** How large it is drawn, for the row it sits in; none in a button of the library's, which sizes its icon. */
		class?: ClassValue;
	}

	let { folded, class: size }: Props = $props();
</script>

<!-- One chevron for everything that folds, at the far end of what it folds: pointing down while what it
	folds is away, as pressing it opens that below; up while it is open, as pressing it folds that up -->
<Icon name="chevron" class={[size, 'transition-transform', !folded && 'rotate-180']} />
