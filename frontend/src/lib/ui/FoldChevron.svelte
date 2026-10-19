<script lang="ts">
	import Icon from './Icon.svelte';

	interface Props {
		folded: boolean;
	}

	let { folded }: Props = $props();
</script>

<!-- One chevron for everything that folds, at the far end of what it folds, at the size of the small words and
	buttons it stands among: pointing down while what it folds is away, as pressing it opens that below; up while
	it is open, as pressing it folds that up -->
<Icon name="chevron" size="xs" pointing={folded ? 'down' : 'up'} />
