export interface CommentPart {
  kind: "prose" | "suggestion";
  text: string;
}

const FENCE = /```suggestion\n([\s\S]*?)```/g;

/**
 * Split a comment into what was written and what was suggested.
 *
 * A suggestion is code the reader wants in place of what is there, so it is
 * shown as code rather than as prose in the reading face.
 */
export function splitSuggestions(body: string): CommentPart[] {
  const parts: CommentPart[] = [];
  let at = 0;

  for (const match of body.matchAll(FENCE)) {
    const before = body.slice(at, match.index).trim();
    if (before) parts.push({ kind: "prose", text: before });
    parts.push({ kind: "suggestion", text: match[1].replace(/\n$/, "") });
    at = match.index + match[0].length;
  }

  const rest = body.slice(at).trim();
  if (rest) parts.push({ kind: "prose", text: rest });
  return parts.length > 0 ? parts : [{ kind: "prose", text: body }];
}
