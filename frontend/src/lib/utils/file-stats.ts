import type { DiffFile } from "$lib/types";

export interface FileStats {
  additions: number;
  deletions: number;
}

export function fileStats(file: DiffFile): FileStats {
  let additions = 0;
  let deletions = 0;
  for (const hunk of file.hunks) {
    for (const line of hunk.lines) {
      if (line.kind === "add") additions++;
      else if (line.kind === "delete") deletions++;
    }
  }
  return { additions, deletions };
}
