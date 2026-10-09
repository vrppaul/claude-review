/**
 * What each push from the server does to the review on screen, and what the
 * page does when pushes were missed.
 *
 * The connection has already read a push and checked its kind; this decides
 * what it means. The compiler refuses a kind left out of the switch.
 */

import { readReview } from '$lib/api/review-api';
import { caughtUpNote, diffNotTakenNote, notCaughtUpNote, raisedNote, retakenNote } from '$lib/review/panel-notes';
import type { Review } from '$lib/review/review.svelte';
import type { ChangesSince, PointPush, ServerPush, TellingPosition } from '$lib/types';

/** Take in what the server said while the review is open. */
export function handlePush(review: Review, push: ServerPush): void {
	switch (push.type) {
		case 'reply':
			review.threads.receiveReply(push.thread_id, push.body, push.question_id);
			review.sound.announce();
			return;
		case 'answerer':
			review.noteAnswerer(push.attached);
			return;
		case 'chat':
			review.conversation.receive(push.message_id, push.body, push.files);
			review.layout.agentPanel.noteAnswer();
			review.sound.announce();
			return;
		case 'progress':
			review.answerer.showWork(push.work);
			return;
		case 'show':
			// Asked for: the agent does not move this screen on its own
			review.sections.showFile(push.file);
			return;
		case 'status':
			review.answerer.report(push.agent);
			return;
		case 'point':
			raise(review, push);
			return;
		case 'changed':
			// Said, never acted on: swapping the diff under a half-written
			// comment would orphan it
			review.diff.treeMoved.note(push.moved_count);
			return;
		case 'round':
			review.rounds.reach(push.number);
			return;
		case 'diff':
			landed(review, push.file_count, push.changes).catch((error) => {
				// A round landing half-applied is worse than not at all: the code
				// under the reader has moved and their threads have not
				review.conversation.note(diffNotTakenNote(error));
			});
			return;
		default:
			unknown(push);
	}
}

/**
 * A push of a kind this page does not handle. The connection passes over
 * kinds it does not know, and the compiler refuses a known kind left out of
 * the switch above, so this only says so if both are ever wrong.
 */
function unknown(push: never): void {
	console.warn('claude-review: the server pushed something this page does not know', push);
}

/** Put a thread the agent raised onto the diff, and say so in the panel. */
function raise(review: Review, push: PointPush): void {
	// The server quoted it from the diff it checked the lines against
	const id = review.threads.raise(push.thread_id, push.anchor, push.body, push.severity);
	review.conversation.note(raisedNote(push.anchor), [id]);
	review.sound.announce();
}

/**
 * Take in the work a round asked for, now it has landed.
 *
 * The threads move onto the review's own diff — one whose lines survived
 * follows them, one whose lines are gone says so — whatever narrower base
 * is being read on screen. Which files changed is what takes the tick off
 * the ones the agent rewrote.
 */
async function landed(review: Review, fileCount: number, changes: ChangesSince | null): Promise<void> {
	const moved = await review.takeRetakenDiff();
	review.noteRetake(moved, changes);
	// The conversation is about code that has just changed under it, so the
	// panel says where one lot of answers stops applying
	review.conversation.note(retakenNote(fileCount, moved));
}

/**
 * Take in a push the connection hands over, unless the review has it
 * already: another tab may have taken it in first, and its draft been
 * adopted here.
 */
export function takePush(review: Review, push: ServerPush, at: TellingPosition): void {
	if (review.telling.hear(at)) handlePush(review, push);
}

/**
 * Catch up after the connection came back to a review that could not hand
 * over everything it missed; the telling goes on from `from`.
 *
 * What the pushes kept up to date is read again. What they alone carried —
 * an answer in a thread, a thread raised, a word in the panel — is gone, and
 * the panel says so. A retake among them would have left the threads on old
 * lines: following them again moves only those whose lines moved, so it is
 * done whether or not one happened. Which files a missed retake rewrote
 * cannot be told, so the ticks stay as the reader left them.
 */
export async function catchUp(review: Review, from: TellingPosition): Promise<void> {
	review.telling.continueFrom(from);
	try {
		review.learn(await readReview());
		const moved = await review.takeRetakenDiff();
		review.conversation.note(caughtUpNote(moved));
	} catch (error) {
		review.conversation.note(notCaughtUpNote(error));
	}
}
