<script lang="ts">
	import type { LineAnchor } from '$lib/types';
	import { anchorLabel } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import { whereRead } from '$lib/review/files-way';

	// Where a change is shown the same number is on both sides, so a thread says which it hangs on, in the diff's
	// own signs
	const SIDES = {
		old: { sign: '−', class: 'cr-sign-del', title: 'on the line this change removed' },
		new: { sign: '+', class: 'cr-sign-add', title: 'on the new line' }
	} as const;

	interface Props {
		anchor: LineAnchor;
	}

	let { anchor }: Props = $props();
	const review = useReview();

	const side = $derived(SIDES[anchor.side]);
	// What the thread hangs in shows a change, wherever its card is drawn, but in a file read alone: the change did
	// not touch it, and its lines have one side
	const saysSide = $derived(review.mode === 'diff' && whereRead(anchor, review.diff) !== 'in-its-file-alone');
</script>

<!-- Said at the start of the thread's bar, in the page's own words: the side in the diff's own sign, then the line -->
{#if saysSide}
	<span data-testid="comment-side" class={side.class} title={side.title}>{side.sign}</span>
{/if}
<span data-testid="comment-line-label">{anchorLabel(anchor)}</span>
