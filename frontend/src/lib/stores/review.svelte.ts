/**
 * What round the review is in, and whether anything is there to answer it.
 *
 * Sending used to end the review. It can now send a round instead: the
 * threads stay on screen, the agent answers and changes what it changed,
 * and the diff is taken again underneath them. That only makes sense while
 * an agent is actually waiting on the review, which is what `answerer`
 * says — so the controls for it appear when there is someone to talk to.
 */

let round = $state(1);
let answerer = $state(false);

export const reviewStore = {
  get round(): number {
    return round;
  },

  /** Whether a round can be sent, rather than only a final review. */
  get canSendRound(): boolean {
    return answerer;
  },

  setRound(next: number) {
    round = next;
  },

  attachAnswerer() {
    answerer = true;
  },

  clear() {
    round = 1;
    answerer = false;
  },
};
