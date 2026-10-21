<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import Actions from './Actions.svelte';
	import Button from './Button.svelte';
	import PaneQuestion from './PaneQuestion.svelte';

	interface Props {
		/** What is asked: "Discard this comment?" */
		question: string;
		/** What the button that goes ahead says: "Discard". */
		goAhead: string;
		/** What the button that leaves things as they are says: "Keep writing". */
		keep: string;
		onKeep: () => void;
		onGoAhead: () => void;
		testId: string;
	}

	let { question, goAhead, keep, onKeep, onGoAhead, testId }: Props = $props();

	let keepButton: HTMLButtonElement | undefined = $state();

	// Asked in a pane that was already open — a menu's Delete — the act that asked it goes with the keyboard, and
	// the safe answer takes it; asked as a pane opens, the pane gives its first the keyboard, and this gives nothing
	$effect(() => focusWhatRemains(() => keepButton));
</script>

<!-- A question before something is lost, on one line that never wraps, in the pane it is asked in. Its answers are
	its ways out, closer to one another than to the question: the safe one first, which takes the keyboard; the other
	loses what was there, drawn as what destroys. One confirmation draws every such question -->
<div class="cr-ui-confirmation">
	<PaneQuestion {question} testId="{testId}-question" />
	<Actions testId="{testId}-actions">
		{#snippet others()}
			<Button bind:element={keepButton} tone="quiet" size="sm" testId="confirm-keep" onclick={onKeep}>{keep}</Button>
		{/snippet}
		{#snippet main()}
			<Button tone="danger" size="sm" testId="confirm-go-ahead" onclick={onGoAhead}>{goAhead}</Button>
		{/snippet}
	</Actions>
</div>
