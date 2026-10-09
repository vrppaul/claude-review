/**
 * What each push from the server does to the review on screen, and what the
 * page does when pushes were missed.
 *
 * The connection has already read a push and checked its kind; this decides
 * what it means. The compiler refuses a kind left out of the switch.
 */

import { anchorShortPlace } from '$lib/anchors/views';
import { readReview } from '$lib/api/review-api';
import type { Review } from '$lib/review/review.svelte';
import type { ChangesSince, FollowOutcome, PointPush, ServerPush } from '$lib/types';

// What the panel says when pushes were missed that the server could not hand over again
const CONNECTION_LOST = 'connection lost for a while — anything said meanwhile may be missing';
// What stands between the parts of one note in the panel
const NOTE_PARTS = ' · ';

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
				review.conversation.note(
					`the diff could not be taken again — ${error instanceof Error ? error.message : 'reload the review'}`
				);
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
	review.conversation.note(`pointed at ${anchorShortPlace(push.anchor)}`, [id]);
	review.sound.announce();
}

/**
 * Take in the work a round asked for, now it has landed.
 *
 * The threads move onto the review's own diff — one whose lines survived
 * follows them, one whose lines are gone says so — whatever narrower base
 * is being read on screen. Which files changed is what takes the tick off
 * the ones the agent rewrote.
 *
 * The threads go first: the server already holds the new diff, and a
 * thread left on old numbers would be kept that way in the draft, while a
 * diff that failed to arrive comes back with a reload.
 */
async function landed(review: Review, fileCount: number, changes: ChangesSince | null): Promise<void> {
	const moved = await review.threads.follow();
	await review.diff.take();
	review.noteRetake(moved, changes);
	// The conversation is about code that has just changed under it, so the
	// panel says where one lot of answers stops applying
	review.conversation.note(retakenNote(fileCount, moved));
}

/**
 * What a retaken diff did to the threads hanging on it. The count is the
 * review's: a narrower base on screen holds fewer files than it does.
 */
function retakenNote(fileCount: number, outcome: FollowOutcome): string {
	return [`diff retaken · ${fileCount} files`, ...followedParts(outcome)].join(NOTE_PARTS);
}

/** What following the threads did, said only where it did anything. */
function followedParts({ followed, outdated }: FollowOutcome): string[] {
	const parts: string[] = [];
	if (followed > 0) parts.push(`${followed} threads followed their lines`);
	if (outdated > 0) parts.push(`${outdated} outdated`);
	return parts;
}

/**
 * Catch up after the connection came back to a review that could not hand
 * over everything it missed.
 *
 * What the pushes kept up to date is read again. What they alone carried —
 * an answer in a thread, a thread raised, a word in the panel — is gone, and
 * the panel says so. A retake among them would have left the threads on old
 * lines: following them again moves only those whose lines moved, so it is
 * done whether or not one happened. Which files a missed retake rewrote
 * cannot be told, so the ticks stay as the reader left them.
 */
export async function catchUp(review: Review): Promise<void> {
	try {
		review.learn(await readReview());
		const moved = await review.threads.follow();
		await review.diff.take();
		review.conversation.note([CONNECTION_LOST, ...followedParts(moved)].join(NOTE_PARTS));
	} catch (error) {
		review.conversation.note(
			`${CONNECTION_LOST} — and the review could not be read again: ${error instanceof Error ? error.message : 'reload the review'}`
		);
	}
}
