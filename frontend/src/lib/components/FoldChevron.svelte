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

<!-- One chevron for everything that folds: pointing down while open, right while folded -->
<Icon name="chevron" class={[size, 'transition-transform', folded && '-rotate-90']} />
