/**
 * Ids the browser hands out: a kind and a number, in order.
 *
 * Short and readable on purpose. The agent names threads and questions by
 * them — `claude-review reply --thread comment-3` — and reads them in every
 * event, so a random string would cost it on every turn.
 *
 * A review restored from its draft already holds ids of every kind, so a
 * sequence carries on past the highest of its own kind rather than from one:
 * a comment deleted before the reload would otherwise hand its id out twice,
 * and two threads sharing an id edit and delete as one.
 */
export class IdSequence {
  private last = 0;

  constructor(private readonly prefix: string) {}

  /** The next id of this kind. */
  next(): string {
    this.last += 1;
    return `${this.prefix}${this.last}`;
  }

  /**
   * Carry on past every id of this kind among these. Ids of other kinds, and
   * the missing ids of what was written before ids existed, are passed over.
   */
  continuePast(ids: Iterable<string | undefined>): void {
    for (const id of ids) {
      if (id === undefined || !id.startsWith(this.prefix)) continue;
      const number = Number(id.slice(this.prefix.length));
      if (Number.isInteger(number) && number > 0) {
        this.last = Math.max(this.last, number);
      }
    }
  }

  /** Start over, for a review that holds nothing yet. */
  reset(): void {
    this.last = 0;
  }
}
