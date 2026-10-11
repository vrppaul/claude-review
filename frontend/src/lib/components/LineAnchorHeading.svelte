<script lang="ts">
	import type { LineAnchor } from '$lib/types';
	import { anchorLabel } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';

	// In a diff the same number is on both sides, so a thread says which it hangs on, in the diff's own signs
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
</script>

{#if review.mode === 'diff'}
	<span data-testid="comment-side" class="font-mono text-xs {side.class}" title={side.title}>{side.sign}</span>
{/if}
<span data-testid="comment-line-label" class="cr-comment-ref font-mono text-xs">{anchorLabel(anchor)}</span>
