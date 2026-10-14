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

	// What the agent writes first, marked only while the story is being written
	const writtenFirst = $derived(waiting && 'cr-sketch-writing');
</script>

<!-- A story, sketched in the review's own colours, so it follows the theme: one drawing wherever Story is offered
	or awaited. No words: what it stands beside says them -->
<div data-testid="story-sketch" class={['cr-sketch', waiting && 'cr-sketch-waiting']} aria-hidden="true">
	<!-- The contents: a chapter read, the one being read with its files, one still to read, on their axis -->
	<div class="cr-sketch-contents">
		<span class="cr-sketch-axis"></span>
		<div class="cr-sketch-chapter cr-sketch-chapter-read">
			<span class={['cr-sketch-node', writtenFirst]}></span>
			<span class={['cr-sketch-bar', writtenFirst]}></span>
		</div>
		<div class="cr-sketch-chapter cr-sketch-chapter-current">
			<span class="cr-sketch-node"></span>
			<span class="cr-sketch-bar"></span>
		</div>
		<div class="cr-sketch-files">
			<span class="cr-sketch-file cr-sketch-file-added">
				<span class="cr-sketch-dot"></span>
				<span class="cr-sketch-bar"></span>
			</span>
			<span class="cr-sketch-file cr-sketch-file-modified">
				<span class="cr-sketch-dot"></span>
				<span class="cr-sketch-bar"></span>
			</span>
		</div>
		<div class="cr-sketch-chapter cr-sketch-chapter-unread">
			<span class="cr-sketch-node"></span>
			<span class="cr-sketch-bar"></span>
		</div>
	</div>
	<!-- The page: the overview in the agent's voice, its last line the doubt; a diagram; a step's reason over its code -->
	<div class="cr-sketch-page">
		<div class="cr-sketch-voice">
			<span class={['cr-sketch-bar cr-sketch-task', writtenFirst]}></span>
			<span class="cr-sketch-bar cr-sketch-done"></span>
			<span class="cr-sketch-bar cr-sketch-doubt"></span>
		</div>
		<div class="cr-sketch-diagram">
			<span class="cr-sketch-box"></span>
			<span class="cr-sketch-link"></span>
			<span class="cr-sketch-box cr-sketch-box-lit"></span>
			<span class="cr-sketch-link"></span>
			<span class="cr-sketch-box"></span>
		</div>
		<div class="cr-sketch-voice cr-sketch-reason">
			<span class="cr-sketch-bar"></span>
			<span class="cr-sketch-bar"></span>
		</div>
		<div class="cr-sketch-hunk">
			<span class="cr-sketch-added"></span>
			<span class="cr-sketch-added"></span>
			<span class="cr-sketch-added"></span>
		</div>
	</div>
</div>
