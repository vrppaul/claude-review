<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ClassValue } from 'svelte/elements';
	import { KEPT_IN_SIGHT_ROLE } from '$lib/dom/in-sight';

	interface Props {
		testId: string;
		/** What its view adds to how it looks, if anything: the files' own steps back once its file is viewed. */
		class?: ClassValue;
		children: Snippet;
	}

	let { testId, class: added, children }: Props = $props();
</script>

<!-- The head of a section of a file's lines: the file's name and what is said and offered beside it,
	kept in sight while the lines scroll under it -->
<div
	data-testid={testId}
	data-role={KEPT_IN_SIGHT_ROLE}
	class={[
		'cr-file-header flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-base-300 bg-base-200 px-3 py-2',
		added
	]}
>
	{@render children()}
</div>
