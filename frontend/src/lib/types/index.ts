export type LineType = "context" | "add" | "delete";
/** Which version of the file a line belongs to. Removed lines are "old". */
export type LineSide = "old" | "new";
export type FileStatus = "modified" | "added" | "deleted" | "renamed";
export type ReviewMode = "diff" | "files" | "transcript";
export type ContentViewMode = "raw" | "preview" | "side-by-side";

export interface DiffLine {
  type: LineType;
  old_no: number | null;
  new_no: number | null;
  content: string;
}

export interface DiffHunk {
  header: string;
  old_start: number;
  new_start: number;
  lines: DiffLine[];
}

export interface DiffFile {
  path: string;
  status: FileStatus;
  hunks: DiffHunk[];
  is_binary: boolean;
  old_mode: string | null;
  new_mode: string | null;
}

export interface DiffResponse {
  files: DiffFile[];
  mode: ReviewMode;
  title: string;
}

export interface Comment {
  id: string;
  file: string;
  side: LineSide;
  start_line: number;
  end_line: number;
  body: string;
}

export interface SubmitRequest {
  comments: Omit<Comment, "id">[];
  body?: string;
}

export interface SubmitResponse {
  markdown: string;
  comment_count: number;
}
