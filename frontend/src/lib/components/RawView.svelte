<script lang="ts">
	import type { DiffLine } from '$lib/types';
	import { useReview } from '$lib/review/context';
	import type { FileDrawing } from './file-drawing.svelte';
	import HunkGap from './HunkGap.svelte';
	import LineGutter from './LineGutter.svelte';
	import LineNotes from './LineNotes.svelte';

	// Columns a row spans: two numbers, the sign and the code in a diff; one number and the code otherwise
	const DIFF_COLUMNS = 4;
	const PLAIN_COLUMNS = 2;
	// The sign a diff writes before each kind of line
	const SIGNS: Record<DiffLine['kind'], string> = { add: '+', delete: '-', context: ' ' };
	// How a row is tinted for the change on it
	const TINTS: Record<DiffLine['kind'], string> = { add: 'cr-row-add', delete: 'cr-row-del', context: '' };

	interface Props {
		/** The file made ready to draw, by whoever draws it. */
		drawing: FileDrawing;
	}

	let { drawing }: Props = $props();
	const review = useReview();

	const isDiffMode = $derived(review.mode === 'diff');
	const columns = $derived(isDiffMode ? DIFF_COLUMNS : PLAIN_COLUMNS);
	const commenting = $derived(drawing.commenting);

	/** A row's tint, with the mark of lines being written about added to the change rather than replacing it. */
	function rowClass(kind: DiffLine['kind'], marked: boolean): string {
		const change = isDiffMode ? TINTS[kind] : '';
		return marked ? `${change} cr-row-marked` : change;
	}
</script>

<div data-testid="raw-view">
	{#each drawing.hunks() as hunk (hunk.key)}
		<div class="border-b border-base-300">
			{#if isDiffMode}
				<HunkGap gap={hunk.gap} header={hunk.header} {drawing} />
			{/if}

			<!-- Fixed layout so every hunk's gutters line up: the automatic
				algorithm sizes each table from its own rows, and a hunk whose
				line numbers are wider would step the columns out of line. -->
			<table class="cr-code w-full table-fixed border-collapse font-mono">
				<colgroup>
					{#if isDiffMode}
						<col class="w-12" />
					{/if}
					<col class="w-12" />
					{#if isDiffMode}
						<col class="w-4" />
					{/if}
					<col />
				</colgroup>
				<tbody>
					{#each hunk.lines as drawn (drawn.key)}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<tr
							class="cr-row {rowClass(drawn.line.kind, commenting.isMarked(drawn.place))} hover:brightness-110"
							onmouseenter={() => commenting.enter(drawn)}
						>
							{#if isDiffMode}
								<td class="cr-gutter w-12 p-0 text-right select-none">
									<LineGutter {drawn} side="old" stop={false} {commenting} />
								</td>
							{/if}
							<td class="cr-gutter w-12 border-r border-base-300 p-0 text-right select-none">
								<LineGutter {drawn} side="new" stop {commenting} />
							</td>
							{#if isDiffMode}
								<td class="cr-sign w-4 px-1 text-center select-none">
									{SIGNS[drawn.line.kind]}
								</td>
							{/if}
							<td class="cr-code-cell px-2 pr-4 whitespace-pre-wrap">
								{@html drawn.markup}
							</td>
						</tr>

						{#if commenting.hasNotes(drawn.place)}
							<tr>
								<td colspan={columns}>
									<LineNotes {commenting} place={drawn.place} />
								</td>
							</tr>
						{/if}
					{/each}
				</tbody>
			</table>
		</div>
	{/each}
</div>
