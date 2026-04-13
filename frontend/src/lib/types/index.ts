export type LineType = "context" | "add" | "delete";
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
}

export interface DiffResponse {
  files: DiffFile[];
  mode: ReviewMode;
}

export interface Comment {
  id: string;
  file: string;
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
