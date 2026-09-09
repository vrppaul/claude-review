import type {
  Comment,
  CommentSeverity,
  LineSide,
  SubmitResponse,
} from "$lib/types";
import { clearDraft, loadDraft, saveDraft } from "$lib/utils/drafts";

let comments = $state<Comment[]>([]);
let reviewBody = $state("");
let submitted = $state(false);

let nextId = 0;
// What the draft is tied to, so it is not restored onto another review
let draftTitle = $state<string | null>(null);
// Where the reader is in the list, shared by every control that steps it
let cursor = $state(-1);

function generateId(): string {
  return `comment-${++nextId}`;
}

function idNumber(id: string): number {
  const parsed = Number.parseInt(id.replace("comment-", ""), 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

function remember(): void {
  if (draftTitle === null) return;
  saveDraft({ title: draftTitle, comments, reviewBody });
}

export const commentStore = {
  get comments() {
    return comments;
  },
  get count() {
    return comments.length;
  },
  get reviewBody() {
    return reviewBody;
  },
  get hasContent() {
    return comments.length > 0 || reviewBody.trim().length > 0;
  },
  get submitted() {
    return submitted;
  },

  /** Step to the next or previous comment, and say which it is. */
  step(direction: 1 | -1): Comment | undefined {
    if (comments.length === 0) return undefined;
    cursor = (cursor + direction + comments.length) % comments.length;
    return comments[cursor];
  },

  setReviewBody(text: string) {
    reviewBody = text;
    remember();
  },

  /**
   * Pick up an unsent review of the same thing, and keep saving from now on.
   *
   * Returns how many comments came back, so the reader can be told rather
   * than left to wonder where they came from.
   */
  restore(title: string): number {
    draftTitle = title;
    const draft = loadDraft(title);
    if (!draft) return 0;

    comments = draft.comments;
    reviewBody = draft.reviewBody ?? "";
    // Past the highest id in the draft, not past its length: deleting a
    // comment before saving would otherwise hand its id out a second time,
    // and two comments sharing an id edit and delete as one.
    nextId = comments.reduce(
      (highest, c) => Math.max(highest, idNumber(c.id)),
      0,
    );
    return comments.length;
  },

  add(
    file: string,
    side: LineSide,
    startLine: number,
    endLine: number,
    body: string,
    severity: CommentSeverity = "note",
  ) {
    const comment: Comment = {
      id: generateId(),
      file,
      side,
      severity,
      start_line: startLine,
      end_line: endLine,
      body,
    };
    comments = [...comments, comment];
    remember();
    return comment.id;
  },

  update(id: string, body: string, severity?: CommentSeverity) {
    comments = comments.map((c) =>
      c.id === id ? { ...c, body, severity: severity ?? c.severity } : c,
    );
    remember();
  },

  remove(id: string) {
    comments = comments.filter((c) => c.id !== id);
    remember();
  },

  getForFile(file: string): Comment[] {
    return comments.filter((c) => c.file === file);
  },

  /** Comments anchored to the end of their range on this exact row. */
  getForLine(file: string, side: LineSide, line: number): Comment[] {
    return comments.filter(
      (c) => c.file === file && c.side === side && c.end_line === line,
    );
  },

  clear() {
    comments = [];
    reviewBody = "";
    submitted = false;
    nextId = 0;
    cursor = -1;
    draftTitle = null;
  },

  async submit(): Promise<SubmitResponse> {
    const trimmedBody = reviewBody.trim();
    const payload = {
      comments: comments.map(
        ({ file, side, severity, start_line, end_line, body }) => ({
          file,
          side,
          severity,
          start_line,
          end_line,
          body,
        }),
      ),
      ...(trimmedBody ? { body: trimmedBody } : {}),
    };

    const response = await fetch("/api/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Submit failed: ${response.status}`);
    }

    const result: SubmitResponse = await response.json();
    submitted = true;
    // The review has left; keeping it would greet the next one as unsent work
    clearDraft();
    return result;
  },
};
