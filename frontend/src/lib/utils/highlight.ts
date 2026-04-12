import hljs from "highlight.js/lib/core";

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

export function highlightLine(
  content: string,
  language: string | null,
): string {
  if (!language || !content.trim()) return escapeHtml(content);
  try {
    return hljs.highlight(content, { language, ignoreIllegals: true }).value;
  } catch {
    return escapeHtml(content);
  }
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
