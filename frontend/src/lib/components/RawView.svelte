<script lang="ts">
	import type { DiffLine, LineSide } from '$lib/types';
	import type { DrawnLine } from '$lib/utils/drawn-file';
	import { useReview } from '$lib/review/context';
	import type { FileDrawing } from './file-drawing.svelte';
	import HunkGap from './HunkGap.svelte';
	import LineGutter from './LineGutter.svelte';
	import type { Reach } from './line-commenting.svelte';
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

	/**
	 * How the keyboard reaches a row's number on one side. Both numbers are
	 * the same line, so one is the row's stop: the one on the line's own side
	 * — a removed line's old number, any other line's new one.
	 */
	function reachOf(drawn: DrawnLine, side: LineSide): Reach {
		return drawn.place.side === side ? 'row-stop' : 'pointer';
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
						<tr
							class="cr-row {rowClass(drawn.line.kind, commenting.isMarked(drawn.place))} hover:brightness-110"
							onmouseenter={() => commenting.enter(drawn)}
						>
							{#if isDiffMode}
								<td class="cr-gutter w-12 p-0 text-right select-none">
									<LineGutter {drawn} side="old" reach={reachOf(drawn, 'old')} {commenting} />
								</td>
							{/if}
							<td class="cr-gutter w-12 border-r border-base-300 p-0 text-right select-none">
								<LineGutter {drawn} side="new" reach={reachOf(drawn, 'new')} {commenting} />
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
	{#if isDiffMode && drawing.end}
		<HunkGap gap={drawing.end} header="" {drawing} />
	{/if}
</div>
