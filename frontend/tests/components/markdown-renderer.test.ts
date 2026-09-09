import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';

describe('MarkdownRenderer', () => {
	it('renders headings as HTML', () => {
		const { getByTestId } = render(MarkdownRenderer, { props: { text: '# Hello World' } });

		const container = getByTestId('markdown-content');
		const heading = container.querySelector('h1');
		expect(heading?.textContent).toBe('Hello World');
	});

	it('renders paragraphs', () => {
		const { getByTestId } = render(MarkdownRenderer, { props: { text: 'Some paragraph text' } });

		const container = getByTestId('markdown-content');
		const paragraph = container.querySelector('p');
		expect(paragraph?.textContent).toBe('Some paragraph text');
	});

	it('renders fenced code blocks', () => {
		const markdown = '```typescript\nconst x = 1;\n```';
		const { getByTestId } = render(MarkdownRenderer, { props: { text: markdown } });

		const container = getByTestId('markdown-content');
		const code = container.querySelector('code');
		expect(code?.textContent).toContain('const x = 1;');
	});

	it('renders lists', () => {
		const markdown = '- item one\n- item two';
		const { getByTestId } = render(MarkdownRenderer, { props: { text: markdown } });

		const container = getByTestId('markdown-content');
		const items = container.querySelectorAll('li');
		expect(items).toHaveLength(2);
		expect(items[0].textContent).toBe('item one');
		expect(items[1].textContent).toBe('item two');
	});

	it('renders a heading as a heading, not as its source', () => {
		const { getByTestId } = render(MarkdownRenderer, { props: { text: '# Title' } });

		const heading = getByTestId('markdown-content').querySelector('h1');
		expect(heading?.textContent).toBe('Title');
	});
});

describe('a previewed file is read, not run', () => {
	it('shows raw HTML instead of rendering it', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: '# Doc\n\n<img src=x onerror="alert(1)">\n' }
		});

		const content = getByTestId('markdown-content');
		expect(content.querySelector('img')).toBeNull();
		expect(content.textContent).toContain('<img src=x onerror="alert(1)">');
	});

	it('does not render a script tag from the file under review', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: '<script>window.pwned = 1<\/script>\n' }
		});

		expect(getByTestId('markdown-content').querySelector('script')).toBeNull();
	});

	it('leaves a link that is code rather than a destination as text', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: '[click me](javascript:alert(1))\n' }
		});

		const content = getByTestId('markdown-content');
		expect(content.querySelector('a')).toBeNull();
		expect(content.textContent).toContain('click me');
	});

	it('still renders an ordinary link', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: '[docs](https://example.com/a)\n' }
		});

		const link = getByTestId('markdown-content').querySelector('a');
		expect(link?.getAttribute('href')).toBe('https://example.com/a');
	});

	it('still renders a relative link', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: '[other](./other.md)\n' }
		});

		expect(getByTestId('markdown-content').querySelector('a')?.getAttribute('href')).toBe(
			'./other.md'
		);
	});

	it('keeps code blocks escaped rather than double-escaped', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: '```js\nconst a = 1 < 2 && 3 > 2;\n```\n' }
		});

		expect(getByTestId('markdown-content').textContent).toContain('const a = 1 < 2 && 3 > 2;');
	});
});
