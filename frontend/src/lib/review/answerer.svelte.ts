/**
 * Whoever answers the review: whether anyone is there, what it last said
 * about itself, and what it says it is doing.
 *
 * Rounds only make sense while an agent is actually waiting on the review,
 * so the controls for them appear when there is someone to talk to.
 */

import type { AgentStatus, AgentWork } from "$lib/types";

export class Answerer {
  #attached: boolean;
  #status: AgentStatus;
  // The state of the work in progress, so it is never kept and never
  // outlives the work: whether it is over is the server's to say
  #work = $state<AgentWork | null>(null);

  constructor(attached: boolean, status: AgentStatus) {
    this.#attached = $state(attached);
    this.#status = $state(status);
  }

  /** Whether an agent is waiting on the review, so a round can be sent. */
  get attached(): boolean {
    return this.#attached;
  }

  /** What the agent last said about itself, with the time it said it. */
  get status(): AgentStatus {
    return this.#status;
  }

  /** What the agent says it is doing, or nothing once the work is over. */
  get work(): AgentWork | null {
    return this.#work;
  }

  /** An agent turned up, or went quiet long enough to count as gone. */
  setAttached(attached: boolean): void {
    this.#attached = attached;
  }

  report(status: AgentStatus): void {
    this.#status = status;
  }

  /**
   * Show the work as the server says it now stands. Whole every time, so
   * every tab on the review shows the same.
   */
  showWork(work: AgentWork | null): void {
    this.#work = work;
  }
}
