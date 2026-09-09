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
