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
      if (line.type === "add") additions++;
      else if (line.type === "delete") deletions++;
    }
  }
  return { additions, deletions };
}
