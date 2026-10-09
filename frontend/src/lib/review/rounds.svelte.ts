/**
 * Which round the review is in.
 *
 * Sending used to end the review. It can now send a round instead: the
 * threads stay on screen, the agent answers and changes what it changed,
 * and the diff is taken again underneath them. Rounds only go forward, and
 * every side that knows one — the server as the page opens, a push, the
 * draft, a round just sent — moves it forward the same way: a restarted
 * server comes back believing it is round one, and the page is then the
 * only side that still knows better.
 */
export class Rounds {
  #current: number;

  constructor(first: number) {
    this.#current = $state(first);
  }

  /** The round being written. */
  get current(): number {
    return this.#current;
  }

  /** Move to a round somebody knows the review has reached; never back. */
  reach(round: number): void {
    this.#current = Math.max(this.#current, round);
  }
}
