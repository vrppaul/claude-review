<script lang="ts">
	import Icon from '$lib/ui/Icon.svelte';

	interface Props {
		folded: boolean;
	}

	let { folded }: Props = $props();
</script>

<!-- One chevron for everything that folds, at the far end of what it folds: pointing down while what it
	folds is away, as pressing it opens that below; up while it is open, as pressing it folds that up -->
<Icon name="chevron" size="xs" pointing={folded ? 'down' : 'up'} />
