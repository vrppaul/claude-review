<script lang="ts">
	import type { ClassValue } from 'svelte/elements';
	import { counted } from '$lib/utils/words';

	interface Props {
		/** The files the agent called housekeeping, by their paths. */
		paths: string[];
		testId: string;
		/** How it is set where it stands: under the story, or under its contents. */
		class: ClassValue;
	}

	let { paths, testId, class: set }: Props = $props();
</script>

<!-- What the agent called housekeeping: named, quiet and folded away, and drawn nowhere -->
<details data-testid={testId} class={set}>
	<summary class="cursor-pointer">
		Housekeeping · {counted(paths.length, { one: 'file', many: 'files' })}
	</summary>
	<ul class="mt-2 flex flex-col gap-0.5 font-mono text-xs">
		{#each paths as path (path)}
			<li class="wrap-anywhere">{path}</li>
		{/each}
	</ul>
</details>
