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
import type { HeardPush } from '$lib/review/telling.svelte';
import type { DiffPush, PointPush, ServerPush, TellingPosition } from '$lib/types';

/** A push that says something of the review's facts, which the draft does not keep. */
type FactPush = Exclude<ServerPush, { type: 'reply' | 'chat' | 'point' | 'diff' }>;

/**
 * Take in what the server said while the review is open.
 *
 * What a push adds to the draft — an answer, a raised thread, a note — is
 * added once, however often the push arrives. What it says of the review's
 * facts — its agent, its round, its diff — is taken in only when the facts
 * the page read do not hold it already.
 */
function handlePush(review: Review, push: ServerPush, heard: HeardPush): void {
	switch (push.type) {
		case 'reply':
			if (review.threads.receiveReply(push.thread_id, push.body, push.question_id, heard.at)) {
				review.sound.announce();
			}
			return;
		case 'chat':
			if (review.conversation.receive(push.message_id, push.body, push.files, heard.at)) {
				review.layout.agentPanel.noteAnswer();
				review.sound.announce();
			}
			return;
		case 'point':
			raise(review, push, heard.at);
			return;
		case 'diff':
			landed(review, push, heard).catch((error) => {
				// A round landing half-applied is worse than not at all: the code
				// under the reader has moved and their threads have not
				review.conversation.note(diffNotTakenNote(error));
			});
			return;
		default:
			if (!heard.factsHoldIt) learnFrom(review, push);
	}
}

/** Take in what a push says of the review's facts, which the draft does not keep. */
function learnFrom(review: Review, push: FactPush): void {
	switch (push.type) {
		case 'answerer':
			review.noteAnswerer(push.attached);
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
		case 'changed':
			// Said, never acted on: swapping the diff under a half-written
			// comment would orphan it
			review.diff.treeMoved.note(push.moved_count);
			return;
		case 'round':
			review.rounds.reach(push.number);
			return;
		default:
			unknown(push);
	}
}

/**
 * A push of a kind this page does not handle. The connection passes over
 * kinds it does not know, and the compiler refuses a known kind left out of
 * the switches above, so this only says so if both are ever wrong.
 */
function unknown(push: never): void {
	console.warn('claude-review: the server pushed something this page does not know', push);
}

/** Put a thread the agent raised onto the diff, and say so in the panel. */
function raise(review: Review, push: PointPush, pushedAt: TellingPosition): void {
	// The server quoted it from the diff it checked the lines against
	if (!review.threads.raise(push.thread_id, push.anchor, push.body, push.severity)) return;
	review.conversation.note(raisedNote(push.anchor), { threads: [push.thread_id], pushedAt });
	review.sound.announce();
}

/**
 * Take in the work a round asked for, now it has landed.
 *
 * The threads move onto the review's own diff — one whose lines survived
 * follows them, one whose lines are gone says so — whatever narrower base
 * is being read on screen. Which files changed is what takes the tick off
 * the ones the agent rewrote. A diff the page read after the retake is
 * already the retaken one: only the threads move.
 */
async function landed(review: Review, push: DiffPush, heard: HeardPush): Promise<void> {
	const moved = heard.factsHoldIt ? await review.followThreads() : await review.takeRetakenDiff();
	if (!heard.factsHoldIt) review.noteRetake(moved, push.changes);
	// The conversation is about code that has just changed under it, so the
	// panel says where one lot of answers stops applying
	review.conversation.note(retakenNote(push.file_count, moved), { pushedAt: heard.at });
}

/** Take in a push the connection hands over, unless this page's socket handed it over before. */
export function takePush(review: Review, push: ServerPush, at: TellingPosition): void {
	const heard = review.telling.hear(at);
	if (heard !== null) handlePush(review, push, heard);
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
