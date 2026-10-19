<script lang="ts">
	import { BECAME, type Became } from './status-letter';

	interface Props {
		/** The letter it is said in: "M". */
		letter: string;
		became: Became;
		/** The word for it, for whoever cannot see the letter or tell its colour: "modified". */
		said: string;
	}

	let { letter, became, said }: Props = $props();
</script>

<!-- What became of a file, as a letter in the change's own colour beside its name, rather than a filled disc: the
	name is what the eye should land on (lib/ui/status-letter.ts); and the word for it, for whoever cannot see the
	letter or tell its colour -->
<span aria-hidden="true" class={['cr-ui-status-letter', BECAME[became]]}>{letter}</span>
<span class="sr-only">{said}</span>
