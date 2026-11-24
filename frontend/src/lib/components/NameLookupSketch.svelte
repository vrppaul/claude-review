<script lang="ts">
	import Key from '$lib/ui/Key.svelte';
	import { LOOKUP_CHORD, pointerChordName } from './keymap';

	/** A line of code a name stands in: the code before the name, and after it. */
	interface AroundTheName {
		before: string;
		after: string;
	}

	/** A place the name stands in, as the pane lists it: its line, and the file it is in. */
	interface Place extends AroundTheName {
		file: string;
	}

	// The name looked up, the line it is pressed in, and the places the pane lists, short enough for the card
	const NAME = 'FailedAttempts';
	const PRESSED_IN: AroundTheName = { before: 'new ', after: '()' };
	const PLACES: Place[] = [
		{ before: 'class ', after: ' {', file: 'attempts.ts' },
		{ before: 'attempts: ', after: ',', file: 'signIn.ts' },
		{ before: 'import { ', after: ' }', file: 'routes.ts' }
	];
	// Where the name pressed starts in its line, and how long it is, in the code's characters: the pane's arrow
	// points at its middle
	const NAME_FROM = `${PRESSED_IN.before.length}ch`;
	const NAME_LENGTH = `${NAME.length}ch`;
</script>

<!-- A name looked up, sketched on the review's own grounds, marks and code face, so it follows the theme: a line of
	code, the name in it pressed with the gesture's keys, and the pane under it of the places the name stands in, the
	name marked the same in each -->
<div data-testid="name-lookup-sketch" class="cr-sketch cr-name-sketch" aria-hidden="true">
	<div class="cr-name-sketch-line">
		<span>
			{PRESSED_IN.before}<span class="cr-name-sketch-name cr-name-sketch-pressed"
				>{NAME}<svg class="cr-name-sketch-pointer" width="11" height="16" viewBox="-0.5 -0.5 11 16">
					<path d="M 0 0 L 0 13 L 3.5 9.8 L 6 15 L 8.2 14 L 5.8 9 L 10.5 9 Z" stroke-linejoin="round" />
				</svg></span
			>{PRESSED_IN.after}
		</span>
		<Key keys={pointerChordName(LOOKUP_CHORD)} stands="listed" testId="name-lookup-sketch-keys" />
	</div>
	<div
		class="cr-name-sketch-pane"
		style:--cr-name-sketch-name-from={NAME_FROM}
		style:--cr-name-sketch-name-length={NAME_LENGTH}
	>
		<svg class="cr-name-sketch-arrow" width="12" height="7" viewBox="-6 -0.5 12 7">
			<path class="cr-name-sketch-arrow-ground" d="M -5.5 6 L 0 0.5 L 5.5 6 Z" />
			<path class="cr-name-sketch-arrow-edge" d="M -5.5 6 L 0 0.5 L 5.5 6" />
		</svg>
		{#each PLACES as place (place.file)}
			<div class="cr-name-sketch-place">
				<span>{place.before}<span class="cr-name-sketch-name">{NAME}</span>{place.after}</span>
				<span class="cr-name-sketch-file">{place.file}</span>
			</div>
		{/each}
	</div>
</div>
