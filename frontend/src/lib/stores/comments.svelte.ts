import type {
  Comment,
  CommentSeverity,
  LineSide,
  SubmitResponse,
} from "$lib/types";

let comments = $state<Comment[]>([]);
let reviewBody = $state("");
let submitted = $state(false);

let nextId = 0;

function generateId(): string {
  return `comment-${++nextId}`;
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

  setReviewBody(text: string) {
    reviewBody = text;
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
    return comment.id;
  },

  update(id: string, body: string, severity?: CommentSeverity) {
    comments = comments.map((c) =>
      c.id === id ? { ...c, body, severity: severity ?? c.severity } : c,
    );
  },

  remove(id: string) {
    comments = comments.filter((c) => c.id !== id);
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
    return result;
  },
};
