<script lang="ts">
	import type { ClassValue } from 'svelte/elements';
	import { LINE_CODE_ROLE } from '$lib/dom/line-code';
	import type { DiffLine, LineSide } from '$lib/types';
	import LineFailure from '$lib/ui/LineFailure.svelte';
	import type { DrawnLine } from '$lib/utils/drawn-file';
	import type { FileDrawing } from './file-drawing.svelte';
	import HunkGap from './HunkGap.svelte';
	import LineGutter from './LineGutter.svelte';
	import type { Reach } from './line-commenting.svelte';
	import LineNotes from './LineNotes.svelte';

	// Columns a row spans: two numbers, the sign and the code where a change is shown; one number and the code otherwise
	const DIFF_COLUMNS = 4;
	const PLAIN_COLUMNS = 2;
	// The sign a diff writes before each kind of line
	const SIGNS: Record<DiffLine['kind'], string> = { add: '+', delete: '-', context: ' ' };
	// How a row is tinted for the change on it; a line the change kept is not
	const TINTS: Record<DiffLine['kind'], string | null> = { add: 'cr-row-add', delete: 'cr-row-del', context: null };

	interface Props {
		/** The file made ready to draw, by whoever draws it. */
		drawing: FileDrawing;
	}

	let { drawing }: Props = $props();

	const showsChange = $derived(drawing.showsChange);
	const columns = $derived(showsChange ? DIFF_COLUMNS : PLAIN_COLUMNS);
	const commenting = $derived(drawing.commenting);
	const naming = $derived(drawing.naming);

	/** A row's tint, with the reader's own mark added to the change rather than replacing it. */
	function rowClass(kind: DiffLine['kind'], marked: boolean): ClassValue {
		return [showsChange && TINTS[kind], marked && 'cr-row-marked'];
	}

	/** Whether a line wears the reader's mark: it is being written about, or it is the one the page took them to. */
	function marked(drawn: DrawnLine): boolean {
		return commenting.isMarked(drawn.place) || drawing.arrivedAt(drawn);
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
		<div class="cr-hunk">
			<HunkGap gap={hunk.gap} header={hunk.header} {drawing} />

			<!-- Fixed layout so every hunk's gutters line up: the automatic
				algorithm sizes each table from its own rows, and a hunk whose
				line numbers are wider would step the columns out of line. -->
			<table class="cr-code w-full table-fixed border-collapse font-mono">
				<colgroup>
					{#if showsChange}
						<col class="w-(--cr-line-number-width)" />
					{/if}
					<col class="w-(--cr-line-number-width)" />
					{#if showsChange}
						<col class="w-(--cr-diff-sign-width)" />
					{/if}
					<col />
				</colgroup>
				<tbody>
					{#each hunk.lines as drawn (drawn.key)}
						<tr
							class={['cr-row', rowClass(drawn.line.kind, marked(drawn))]}
							onmouseenter={() => commenting.enter(drawn)}
						>
							{#if showsChange}
								<td class="cr-gutter w-(--cr-line-number-width) p-0 text-right select-none">
									<LineGutter {drawn} side="old" reach={reachOf(drawn, 'old')} {commenting} />
								</td>
							{/if}
							<td class="cr-gutter w-(--cr-line-number-width) border-r border-base-300 p-0 text-right select-none">
								<LineGutter {drawn} side="new" reach={reachOf(drawn, 'new')} {commenting} />
							</td>
							{#if showsChange}
								<td class="cr-sign w-(--cr-diff-sign-width) px-1 text-center select-none">
									{SIGNS[drawn.line.kind]}
								</td>
							{/if}
							<td
								data-testid="line-code"
								data-role={LINE_CODE_ROLE}
								class="cr-code-cell px-2 pr-4 whitespace-pre-wrap"
								onmousemove={(event) => naming?.point(event, event.currentTarget, drawn)}
								onmouseleave={(event) => naming?.point(event, event.currentTarget, drawn)}
								onclick={(event) => naming?.press(event, event.currentTarget, drawn)}
							>
								{@html drawn.markup}
							</td>
						</tr>

						{#each drawing.failuresUnder(drawn.place) as found (found)}
							<tr>
								<td colspan={columns}>
									<LineFailure
										check={found.check}
										what={found.failure.what}
										why={found.failure.why}
										outOfDate={found.outOfDate}
										testId="line-failure"
									/>
								</td>
							</tr>
						{/each}

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
	{#if drawing.end}
		<HunkGap gap={drawing.end} header="" {drawing} />
	{/if}
</div>
