import hljs from "highlight.js/lib/core";

import type { DiffFile, DiffLine } from "$lib/types";

export { hljs };

// Register common languages
import javascript from "highlight.js/lib/languages/javascript";
import typescript from "highlight.js/lib/languages/typescript";
import python from "highlight.js/lib/languages/python";
import css from "highlight.js/lib/languages/css";
import json from "highlight.js/lib/languages/json";
import xml from "highlight.js/lib/languages/xml";
import bash from "highlight.js/lib/languages/bash";
import yaml from "highlight.js/lib/languages/yaml";
import markdown from "highlight.js/lib/languages/markdown";
import rust from "highlight.js/lib/languages/rust";
import go from "highlight.js/lib/languages/go";
import sql from "highlight.js/lib/languages/sql";

hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("python", python);
hljs.registerLanguage("css", css);
hljs.registerLanguage("json", json);
hljs.registerLanguage("xml", xml);
hljs.registerLanguage("html", xml);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("yaml", yaml);
hljs.registerLanguage("markdown", markdown);
hljs.registerLanguage("rust", rust);
hljs.registerLanguage("go", go);
hljs.registerLanguage("sql", sql);

const EXT_TO_LANG: Record<string, string> = {
  ".js": "javascript",
  ".mjs": "javascript",
  ".cjs": "javascript",
  ".jsx": "javascript",
  ".ts": "typescript",
  ".tsx": "typescript",
  ".py": "python",
  ".css": "css",
  ".json": "json",
  ".html": "html",
  ".htm": "html",
  ".xml": "xml",
  ".svg": "xml",
  ".sh": "bash",
  ".bash": "bash",
  ".zsh": "bash",
  ".yml": "yaml",
  ".yaml": "yaml",
  ".md": "markdown",
  ".rs": "rust",
  ".go": "go",
  ".sql": "sql",
  ".svelte": "html",
};

export function detectLanguage(filePath: string): string | null {
  const dot = filePath.lastIndexOf(".");
  if (dot === -1) return null;
  const ext = filePath.slice(dot).toLowerCase();
  return EXT_TO_LANG[ext] ?? null;
}

/**
 * Highlight every row of a file, returning the markup per hunk per line.
 *
 * Highlighting row by row cannot see a construct that spans lines — a
 * docstring, a block comment, a template literal — and colours each
 * continuation as if it began a fresh statement. So each hunk is highlighted
 * as a document instead.
 *
 * A hunk holds two versions of the same region interleaved, and only one of
 * them is real code at a time: a removed line may open a string that the line
 * replacing it never opens. Each side is therefore assembled and highlighted
 * on its own, and every row takes the markup from the side it belongs to.
 * Hunks are highlighted separately because the gaps between them are not part
 * of the file, so state must not carry across one.
 */
export function highlightFile(
  file: DiffFile,
  language: string | null,
): string[][] {
  return file.hunks.map((hunk) => highlightHunk(hunk.lines, language));
}

function highlightHunk(lines: DiffLine[], language: string | null): string[] {
  if (!language) return lines.map((line) => escapeHtml(line.content));

  const hasRemovals = lines.some((line) => line.type === "delete");
  const newSide = sideLines(lines, "add", language);
  const oldSide = hasRemovals ? sideLines(lines, "delete", language) : newSide;

  let oldAt = 0;
  let newAt = 0;
  return lines.map((line) => {
    if (line.type === "delete")
      return oldSide[oldAt++] ?? escapeHtml(line.content);
    if (line.type === "add")
      return newSide[newAt++] ?? escapeHtml(line.content);
    // Context belongs to both versions, so it advances both readers
    const html = newSide[newAt] ?? escapeHtml(line.content);
    oldAt++;
    newAt++;
    return html;
  });
}

/** Highlight one version of a hunk: its context plus the lines exclusive to that side. */
function sideLines(
  lines: DiffLine[],
  exclusive: DiffLine["type"],
  language: string,
): string[] {
  const text = lines
    .filter((line) => line.type === "context" || line.type === exclusive)
    .map((line) => line.content)
    .join("\n");

  try {
    return splitHighlighted(
      hljs.highlight(text, { language, ignoreIllegals: true }).value,
    );
  } catch {
    return text.split("\n").map(escapeHtml);
  }
}

/**
 * Cut highlighted markup into one string per line.
 *
 * A span may run across a newline, so every span still open at a break is
 * closed before the line ends and reopened at the start of the next one —
 * otherwise each line would be invalid markup on its own.
 */
function splitHighlighted(html: string): string[] {
  const lines: string[] = [];
  const open: string[] = [];
  let current = "";
  let i = 0;

  while (i < html.length) {
    const char = html[i];

    if (char === "<") {
      const close = html.indexOf(">", i);
      if (close === -1) {
        current += html.slice(i);
        break;
      }
      const tag = html.slice(i, close + 1);
      if (tag.startsWith("</")) open.pop();
      else if (!tag.endsWith("/>")) open.push(tag);
      current += tag;
      i = close + 1;
      continue;
    }

    if (char === "\n") {
      lines.push(current + "</span>".repeat(open.length));
      current = open.join("");
      i += 1;
      continue;
    }

    current += char;
    i += 1;
  }

  lines.push(current + "</span>".repeat(open.length));
  return lines;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
