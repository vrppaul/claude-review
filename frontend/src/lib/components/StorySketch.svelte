<script lang="ts">
	interface Props {
		/**
		 * Whether the story is being written: the sketch is greyed, and what the
		 * agent writes first — the first chapter, the overview's first line —
		 * stands in its colour, pulsing. Otherwise the sketch is of a story told.
		 */
		waiting?: boolean;
	}

	let { waiting = false }: Props = $props();

	// What the agent writes first breathes only while the story is being written
	const writtenFirst = $derived(waiting && 'cr-sketch-writing');
</script>

<!-- A story, sketched in the review's own colours, so it follows the theme: one drawing wherever Story is offered
	or awaited. No words: what it stands beside says them. Each part is painted by what it is (--cr-sketch-…),
	which the sketch of a story being written greys. Two drawings: the contents keep their width, and the page
	stretches with the box, its lines as long as a share of it -->
<div data-testid="story-sketch" class={['cr-sketch', waiting && 'cr-sketch-waiting']} aria-hidden="true">
	<!-- The contents: a chapter read, the one being read with its files, one still to read, on their axis -->
	<svg class="shrink-0 overflow-visible" width="70" height="84">
		<line class="stroke-(--cr-axis)" x1="5.5" y1="6" x2="5.5" y2="70" />
		<circle class={['fill-(--cr-sketch-written-ring)', writtenFirst]} cx="5.5" cy="5.5" r="8.5" />
		<circle class="fill-base-200" cx="5.5" cy="5.5" r="5" />
		<circle
			class={['fill-(--cr-sketch-read-fill) stroke-(--cr-sketch-written-edge)', writtenFirst]}
			cx="5.5"
			cy="5.5"
			r="5"
		/>
		<rect
			class={['fill-(--cr-sketch-written-title) opacity-(--cr-sketch-faded)', writtenFirst]}
			x="17"
			y="4"
			width="40"
			height="3"
			rx="1.5"
		/>
		<circle class="fill-(--cr-sketch-current-ring)" cx="5.5" cy="23.5" r="8.5" />
		<circle class="fill-base-200 stroke-(--cr-sketch-current-edge)" cx="5.5" cy="23.5" r="5" />
		<rect class="fill-(--cr-sketch-strong)" x="17" y="22" width="46" height="3" rx="1.5" />
		<rect class="fill-base-200 stroke-base-300" x="17.5" y="36.5" width="52" height="18" rx="4" />
		<rect class="fill-(--cr-sketch-added-dot)" x="22" y="41" width="3" height="3" rx="1" />
		<rect class="fill-(--cr-sketch-words)" x="28" y="41" width="30" height="3" rx="1.5" />
		<rect class="fill-(--cr-sketch-modified-dot)" x="22" y="47" width="3" height="3" rx="1" />
		<rect class="fill-(--cr-sketch-words)" x="28" y="47" width="24" height="3" rx="1.5" />
		<circle class="fill-base-200 stroke-(--cr-node-edge)" cx="5.5" cy="67.5" r="5" />
		<rect class="fill-(--cr-sketch-words) opacity-(--cr-sketch-faded)" x="17" y="66" width="36" height="3" rx="1.5" />
	</svg>
	<!-- The page: the overview in the agent's voice, its last line the doubt; a diagram, its heart lit; a step's
		reason over its code, three lines added -->
	<svg class="min-w-0 flex-1 overflow-visible" height="84">
		<rect class="fill-(--cr-agent)" x="0" y="0" width="2" height="17" />
		<rect class={['fill-(--cr-sketch-written-task)', writtenFirst]} x="8" y="0" width="88%" height="3" rx="1.5" />
		<rect class="fill-(--cr-sketch-words)" x="8" y="7" width="72%" height="3" rx="1.5" />
		<rect class="fill-(--cr-sketch-doubt)" x="8" y="14" width="50%" height="3" rx="1.5" />
		<rect class="fill-none stroke-(--cr-node-edge)" x="0.5" y="24.5" width="21" height="9" rx="2" />
		<rect class="fill-(--cr-sketch-words)" x="25" y="28.5" width="8" height="1" />
		<rect class="fill-none stroke-(--cr-sketch-lit)" x="36.5" y="24.5" width="21" height="9" rx="2" />
		<rect class="fill-(--cr-sketch-words)" x="61" y="28.5" width="8" height="1" />
		<rect class="fill-none stroke-(--cr-node-edge)" x="72.5" y="24.5" width="21" height="9" rx="2" />
		<rect class="fill-(--cr-sketch-reason)" x="0" y="41" width="2" height="10" />
		<rect class="fill-(--cr-sketch-words)" x="8" y="41" width="80%" height="3" rx="1.5" />
		<rect class="fill-(--cr-sketch-words)" x="8" y="48" width="58%" height="3" rx="1.5" />
		<rect class="fill-none stroke-base-300" x="0.5" y="58.5" width="100%" height="25" rx="4" />
		<rect class="fill-(--cr-sketch-added-tint)" x="1" y="62" width="70%" height="4" />
		<rect class="fill-(--cr-sketch-added-edge)" x="1" y="62" width="2" height="4" />
		<rect class="fill-(--cr-sketch-added-tint)" x="1" y="69" width="88%" height="4" />
		<rect class="fill-(--cr-sketch-added-edge)" x="1" y="69" width="2" height="4" />
		<rect class="fill-(--cr-sketch-added-tint)" x="1" y="76" width="54%" height="4" />
		<rect class="fill-(--cr-sketch-added-edge)" x="1" y="76" width="2" height="4" />
	</svg>
</div>
