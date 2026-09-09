import { describe, expect, it } from 'vitest';
import { highlightFile } from '$lib/utils/highlight';
import { markRanges, wordRanges, applyWordMarks, type Range } from '$lib/utils/word-diff';
import { hiddenAbove, nextWindow } from '$lib/utils/expansions';
import type { DiffFile, DiffHunk, DiffLine } from '$lib/types';

const L = (type: DiffLine['type'], old_no: number | null, new_no: number | null, content: string): DiffLine => ({ type, old_no, new_no, content });

function strip(html: string): string {
  return html.replace(/<[^>]*>/g, '');
}
function unescape(s: string): string {
  return s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&amp;/g, '&');
}

function file(lines: DiffLine[]): DiffFile {
  return { path: 'a.ts', status: 'modified', is_binary: false, old_mode: null, new_mode: null,
    hunks: [{ header: '@@', old_start: 1, new_start: 1, lines }] };
}

describe('highlight: one entry per line, text preserved', () => {
  const shapes: Record<string, DiffLine[]> = {
    'empty hunk': [],
    'pure add': [L('add', null, 1, 'const a = 1;')],
    'pure delete': [L('delete', 1, null, 'const a = 1;')],
    'unterminated string': [L('delete', 1, null, 'const s = "abc'), L('add', null, 1, 'const s = "abc";'), L('context', 2, 2, 'const t = 2;')],
    'lt in string': [L('context', 1, 1, 'const s = "<div>";'), L('add', null, 2, 'if (a < b) {}')],
    'unequal sides': [L('delete', 1, null, 'a'), L('delete', 2, null, 'b'), L('delete', 3, null, 'c'), L('add', null, 1, 'z')],
    'CR endings': [L('context', 1, 1, 'const a = 1;\r'), L('add', null, 2, 'const b = 2;\r')],
    'delete opens template literal': [
      L('context', 1, 1, 'function f() {'),
      L('delete', 2, null, '  const x = `open'),
      L('add', null, 2, '  const x = 1;'),
      L('context', 3, 3, '}'),
    ],
    'ampersand and entities': [L('delete', 1, null, 'a && b < c'), L('add', null, 1, 'a & b > c')],
    'trailing empty line': [L('add', null, 1, ''), L('add', null, 2, 'x')],
  };

  for (const lang of ['typescript', 'python', null]) {
    for (const [name, lines] of Object.entries(shapes)) {
      it(`${name} / ${lang}`, () => {
        const out = highlightFile(file(lines), lang)[0];
        expect(out.length, 'entry per line').toBe(lines.length);
        lines.forEach((line, i) => {
          expect(unescape(strip(out[i])), `line ${i}`).toBe(line.content);
        });
      });
    }
  }
});

describe('markRanges', () => {
  const cases: [string, string, Range[]][] = [
    ['plain', 'hello world', [[0, 5]]],
    ['range past end', 'abc', [[1, 99]]],
    ['start past end', 'abc', [[10, 20]]],
    ['overlapping', 'abcdefgh', [[0, 4], [2, 6]]],
    ['out of order', 'abcdefgh', [[4, 6], [0, 2]]],
    ['entity at boundary', 'a &amp; b', [[2, 3]]],
    ['entity mid range', 'x &lt;y&gt; z', [[0, 6]]],
    ['bare ampersand no entity', 'a & b', [[0, 3]]],
    ['bare amp with far semicolon', 'a & b; c', [[0, 8]]],
    ['lt with no gt', 'a <b c', [[0, 5]]],
    ['inside spans', '<span class="k">let</span> x', [[1, 5]]],
    ['zero-width range', 'abc', [[1, 1]]],
    ['empty html', '', [[0, 3]]],
  ];
  for (const [name, html, ranges] of cases) {
    it(`preserves text: ${name}`, () => {
      const out = markRanges(html, ranges);
      expect(strip(out), name).toBe(strip(html));
    });
    it(`balanced tags: ${name}`, () => {
      const out = markRanges(html, ranges);
      const opens = (out.match(/<span/g) ?? []).length;
      const closes = (out.match(/<\/span>/g) ?? []).length;
      expect(opens, name).toBe(closes);
    });
  }

  it('marks the right characters (plain text, no entities)', () => {
    const out = markRanges('hello world', [[6, 11]]);
    expect(out).toBe('hello <span class="cr-word">world</span>');
  });

  it('marks the right characters when an entity precedes the range', () => {
    // plain text is: a & bcd   -> indices a=0 ' '=1 '&'=2 ' '=3 b=4 c=5 d=6
    const out = markRanges('a &amp; bcd', [[4, 7]]);
    expect(strip(out)).toBe('a &amp; bcd');
    expect(out).toContain('<span class="cr-word">bcd</span>');
  });
});

describe('markRanges vs an unescaped & in the html', () => {
  it('miscounts when html carries a raw ampersand followed by a nearby semicolon', () => {
    const html = 'a & b; XY';       // plain length 9 if & is one char
    const out = markRanges(html, [[7, 9]]);   // want "XY"
    console.log('RAW-AMP OUT:', JSON.stringify(out));
  });
});

describe('join() mutation', () => {
  it('mutates the ranges array it was handed', () => {
    // exercised through wordRanges; check the returned ranges are sane
    const r = wordRanges('alpha beta gamma', 'alpha delta gamma');
    console.log('wordRanges:', JSON.stringify(r));
  });
});

describe('applyWordMarks round trip', () => {
  it('keeps text through highlight + marks', () => {
    const lines = [
      L('context', 1, 1, 'function f(a, b) {'),
      L('delete', 2, null, '  return a + b; // <old>'),
      L('add', null, 2, '  return a - b; // <new>'),
      L('context', 3, 3, '}'),
    ];
    const html = highlightFile(file(lines), 'typescript')[0];
    const marked = applyWordMarks(lines, html);
    marked.forEach((m, i) => {
      expect(unescape(strip(m)), `line ${i}`).toBe(lines[i].content);
      expect((m.match(/<span/g) ?? []).length).toBe((m.match(/<\/span>/g) ?? []).length);
    });
    console.log('MARKED:', JSON.stringify(marked, null, 1));
  });
});

describe('expansions', () => {
  const H = (new_start: number, lines: DiffLine[]): DiffHunk => ({ header: '@@', old_start: new_start, new_start, lines });

  it('hunk whose last line is an addition', () => {
    const hunks = [
      H(10, [L('context', 10, 10, 'a'), L('add', null, 11, 'b')]),
      H(30, [L('context', 30, 30, 'c')]),
    ];
    expect(hiddenAbove(hunks, 1, 0)).toBe(30 - 11 - 1);
  });

  it('hunk whose last line is a deletion', () => {
    const hunks = [
      H(10, [L('context', 10, 10, 'a'), L('delete', 11, null, 'b')]),
      H(30, [L('context', 30, 29, 'c')]),
    ];
    console.log('last-line-deletion hiddenAbove:', hiddenAbove(hunks, 1, 0));
  });

  it('adjacent hunks', () => {
    const hunks = [
      H(10, [L('context', 10, 10, 'a')]),
      H(11, [L('context', 11, 11, 'b')]),
    ];
    expect(hiddenAbove(hunks, 1, 0)).toBe(0);
    expect(nextWindow(hunks, 1, 0)).toBeNull();
  });

  it('new_start 1', () => {
    const hunks = [H(1, [L('context', 1, 1, 'a')])];
    expect(hiddenAbove(hunks, 0, 0)).toBe(0);
    expect(nextWindow(hunks, 0, 0)).toBeNull();
  });

  it('successive reveals never overlap and terminate', () => {
    const hunks = [H(1, [L('context', 1, 1, 'a')]), H(500, [L('context', 500, 500, 'z')])];
    let revealed = 0;
    const seen: Array<{ start: number; end: number }> = [];
    for (let step = 0; step < 200; step += 1) {
      const w = nextWindow(hunks, 1, revealed);
      if (!w) break;
      seen.push(w);
      expect(w.end).toBeGreaterThanOrEqual(w.start);
      revealed += w.end - w.start + 1;
    }
    expect(nextWindow(hunks, 1, revealed)).toBeNull();
    // no overlap, contiguous downward
    for (let i = 1; i < seen.length; i += 1) {
      expect(seen[i].end).toBe(seen[i - 1].start - 1);
    }
    expect(seen[0].end).toBe(499);
    expect(seen[seen.length - 1].start).toBe(2);
    console.log('windows:', JSON.stringify(seen));
  });

  it('pure-deletion hunk before a gap', () => {
    const hunks = [
      H(4, [L('delete', 5, null, 'x'), L('delete', 6, null, 'y')]),
      H(20, [L('context', 22, 20, 'z')]),
    ];
    console.log('pure-deletion hiddenAbove:', hiddenAbove(hunks, 1, 0), 'window:', JSON.stringify(nextWindow(hunks, 1, 0)));
  });
});
