<script lang="ts">
	import type { Thread } from '$lib/types';
	import { blockKey } from '$lib/anchors/story';
	import { threadPlaceOf } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import { OVERVIEW_PART } from '$lib/review/story-keys';
	import Confirmation from '$lib/ui/Confirmation.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import Menu from '$lib/ui/Menu.svelte';
	import MenuItem from '$lib/ui/MenuItem.svelte';
	import Popover from '$lib/ui/Popover.svelte';
	import { placeKey } from '$lib/utils/line-places';
	import { counted, type CountedWords } from '$lib/utils/words';

	/** What the reader said that the menu is of: the comment that opened the thread, or a reply in it. */
	type Said = 'comment' | 'reply';

	// What the menu's control and its pane are called, said to whoever cannot see the dots
	const MENU = 'Edit or delete';
	const PANES: Record<Said, string> = {
		comment: 'What to do with this comment',
		reply: 'What to do with this reply'
	};
	const EDIT = 'Edit';
	const DELETE = 'Delete';
	const KEEP_IT = 'Keep it';
	// What is asked before a reply, or a comment with nothing under it, is deleted
	const DELETE_QUESTIONS: Record<Said, string> = {
		comment: 'Delete this comment?',
		reply: 'Delete this reply?'
	};
	// What everything said under the comment is called, counted, where deleting it takes them too
	const REPLIES: CountedWords = { one: 'reply', many: 'replies' };

	interface Props {
		thread: Thread;
		/** What it is of: the comment, by the thread's own id, or a reply, by its own. */
		saidId: string;
	}

	let { thread, saidId }: Props = $props();
	const review = useReview();

	let open = $state(false);
	// Whether Delete was chosen, so the pane asks before anything is lost, in the menu's place
	let askingToDelete = $state(false);

	const said = $derived<Said>(saidId === thread.id ? 'comment' : 'reply');
	const deleteQuestion = $derived(deleteQuestionFor(said, thread.turns.length));
	// Deleting the comment deletes the thread it opened; a reply goes alone
	const REMOVE: Record<Said, () => void> = { comment: removeThread, reply: removeReply };

	/** The question before something is deleted, naming everything that goes with it: a comment's replies, counted. */
	function deleteQuestionFor(deleted: Said, replies: number): string {
		if (deleted === 'reply' || replies === 0) return DELETE_QUESTIONS[deleted];
		return `Delete this comment and its ${counted(replies, REPLIES)}?`;
	}

	/** Open or put away the menu; opened, it offers its acts again, never the question it was left on. */
	function setOpen(next: boolean) {
		open = next;
		askingToDelete = false;
	}

	/** Rewrite what was said where it stands: its words become the field. */
	function edit() {
		setOpen(false);
		review.threads.writing.openEdit(thread, saidId);
	}

	/** Delete it: the comment with its thread, or the reply alone. */
	function remove() {
		setOpen(false);
		REMOVE[said]();
	}

	/**
	 * Delete the thread; the keyboard goes back to the line it hung under, or
	 * to what offered the block it hung on, or, for a block the story no
	 * longer draws, to the head of the story the thread stood at.
	 */
	function removeThread() {
		const place = threadPlaceOf(thread.anchor);
		review.threads.remove(thread.id);
		switch (place.on) {
			case 'lines': {
				const { lines } = place;
				review.sections.keyboardToLine(lines.file, placeKey({ side: lines.side, number: lines.end_line }));
				break;
			}
			case 'story':
				// Each gives the keyboard only where it is still on nothing, in the order asked: the block first
				review.sections.keyboardToBlock(blockKey(place.block));
				review.parts.keyboardToHeadOf(OVERVIEW_PART);
				break;
		}
	}

	/** Delete the reply; the keyboard stays with the thread it was in. */
	function removeReply() {
		review.threads.removeTurn(thread.id, saidId);
		review.sections.keyboardToThread(thread.id);
	}
</script>

<!-- What the reader may do to what they said and the agent has not been handed, behind three dots at the head of
	its turn: rewrite it, or delete it, which asks first in the same pane, on one line, counting what goes with it -->
<Popover
	bind:open={() => open, setOpen}
	label={askingToDelete ? deleteQuestion : PANES[said]}
	placement="below-end"
	width="fitted"
	testId="turn-menu-pane"
>
	{#snippet trigger(control)}
		<IconButton {...control} tone="quiet" size="xs" shape="square" label={MENU} testId="turn-menu">
			<Icon name="more" size="xs" />
		</IconButton>
	{/snippet}
	{#if askingToDelete}
		<Confirmation
			question={deleteQuestion}
			goAhead={DELETE}
			keep={KEEP_IT}
			onKeep={() => setOpen(false)}
			onGoAhead={remove}
			testId="delete-dialog"
		/>
	{:else}
		<Menu testId="turn-menu-acts">
			<MenuItem tone="plain" testId="edit-turn" onclick={edit}>
				<Icon name="pencil" size="xs" />
				{EDIT}
			</MenuItem>
			<MenuItem tone="danger" testId="delete-turn" onclick={() => (askingToDelete = true)}>
				<Icon name="trash" size="xs" tone="danger" />
				{DELETE}
			</MenuItem>
		</Menu>
	{/if}
</Popover>
