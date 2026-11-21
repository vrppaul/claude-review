<script lang="ts">
	import { type CodeRead, linesRound } from '$lib/review/places-code.svelte';
	import type { NamePlace } from '$lib/types';
	import BreathingDots from '$lib/ui/BreathingDots.svelte';
	import Button from '$lib/ui/Button.svelte';
	import CodeFrameLines from '$lib/ui/CodeFrameLines.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import { withNameMarked } from '$lib/utils/code-words';

	interface Props {
		/** The place chosen, whose code this is. */
		place: NamePlace;
		/** The name it stands for there, marked on its line. */
		name: string;
		/** What reading its file came to. */
		read: CodeRead;
		/** Read its file again, after a read that failed. */
		readAgain: () => void;
	}

	let { place, name, read, readAgain }: Props = $props();

	// What stands in place of the code while its file is read
	const READING = 'Reading the file';
</script>

<!-- The code round the place chosen: the place's line lit as the change drew it, in its tint and edge, or else as
	the line the reader is at, the name marked on it. While its file is read, that it is; a read that failed says why
	where the code would stand, with the act to read it again -->
{#if read.kind === 'read'}
	<CodeFrameLines reads="running" testId="name-window-lines">
		{#each linesRound(read.lines, place.line) as drawn (drawn.line.new_number)}
			{@const isThePlace = drawn.line.new_number === place.line}
			<tr data-testid="name-window-line" class={['cr-row', isThePlace && (place.added ? 'cr-row-add' : 'cr-row-at')]}>
				<td class="cr-gutter cr-place-number">{drawn.line.new_number}</td>
				<td class="cr-code-cell cr-run-code"
					>{@html isThePlace ? withNameMarked(drawn.markup, drawn.line.content, place.column, name) : drawn.markup}</td
				>
			</tr>
		{/each}
	</CodeFrameLines>
{:else if read.kind === 'failed'}
	<div class="flex flex-col items-start gap-2 p-3">
		<Failure stands="apart" testId="name-window-failed" said={read.why} />
		<!-- It goes as the code comes: whoever reads again hands the keyboard on to what remains -->
		<Button tone="secondary" size="xs" testId="read-code-again" onclick={readAgain}>Try again</Button>
	</div>
{:else}
	<p data-testid="name-window-reading" class="cr-muted flex items-center gap-2 p-3 text-xs">
		<BreathingDots tone="quiet" testId="name-window-dots" />
		{READING}
	</p>
{/if}
