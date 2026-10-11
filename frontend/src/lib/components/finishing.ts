/** What the pane the review is finished from is called: the round it sends, or the end. */
export function finishingTitle(inRounds: boolean, round: number): string {
	return inRounds ? `Round ${round}` : 'Finish the review';
}
