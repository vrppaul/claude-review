<script lang="ts">
	import type { FileStatus } from '$lib/types';
	import { STATUS_LETTERS } from './status-letters';

	interface Props {
		status: FileStatus;
	}

	let { status }: Props = $props();

	const said = $derived(STATUS_LETTERS[status]);
</script>

<!-- What became of a file, as a letter in the change's own colour beside its name; and the word for it,
	for whoever cannot see the letter or tell its colour -->
<span aria-hidden="true" class={['w-3 shrink-0 text-center font-mono text-xs font-semibold', said.colour]}>
	{said.letter}
</span>
<span class="sr-only">{status}</span>
