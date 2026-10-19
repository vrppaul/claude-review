import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';

describe('markdown, previewed', () => {
	it('renders fenced code blocks', () => {
		const markdown = '```typescript\nconst x = 1;\n```';
		const { getByTestId } = render(MarkdownRenderer, { props: { text: markdown } });

		const container = getByTestId('markdown-content');
		const code = container.querySelector('code');
		expect(code?.textContent).toContain('const x = 1;');
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
			props: { text: '<script>window.pwned = 1</script>\n' }
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

	it('opens an ordinary link in a tab of its own, so the review stays where it is', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: '[docs](https://example.com/a)\n' }
		});

		const link = getByTestId('markdown-content').querySelector('a');
		expect(link?.getAttribute('href')).toBe('https://example.com/a');
		expect(link?.getAttribute('target')).toBe('_blank');
		expect(link?.getAttribute('rel')).toBe('noopener noreferrer');
	});

	it.each(['./other.md', 'README.md', '../docs/plan.md', '#usage', '/api/end'])(
		'leaves a relative link (%s) as text: followed, it would take the review away from its own tab',
		(destination) => {
			const { getByTestId } = render(MarkdownRenderer, {
				props: { text: `[where](${destination})\n` }
			});

			const content = getByTestId('markdown-content');
			expect(content.querySelector('a')).toBeNull();
			expect(content.textContent).toContain('where');
		}
	);

	it('keeps an image description and its destination as words, never as markup', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: '![<b onmouseover="alert(1)">chart</b>](<docs/<i>pic</i>.png>)\n' }
		});

		const content = getByTestId('markdown-content');
		expect(content.querySelector('b, i, [onmouseover]')).toBeNull();
		expect(content.textContent).toContain('<b onmouseover="alert(1)">chart</b>');
	});

	it('names an image at a path of the repository in words, inside the line it stands in', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: 'See ![a picture](docs/pic.png) for the layout.\n' }
		});

		const content = getByTestId('markdown-content');
		expect(content.querySelector('img')).toBeNull();
		expect(content.querySelector('a')).toBeNull();
		expect(content.querySelectorAll('p')).toHaveLength(1);
		expect(content.textContent?.trim()).toBe('See image: a picture (docs/pic.png) for the layout.');
	});

	it("never asks the review's own address for an image, where assets/ is the page's own scripts", () => {
		const { getByTestId } = render(MarkdownRenderer, { props: { text: '![logo](assets/logo.png)\n' } });

		const content = getByTestId('markdown-content');
		expect(content.querySelector('img')).toBeNull();
		expect(content.textContent).toContain('image: logo (assets/logo.png)');
	});

	it('opens an image written whole in a tab of its own, rather than drawing it broken', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: '![chart](https://example.com/chart.png)\n' }
		});

		const content = getByTestId('markdown-content');
		const link = content.querySelector('a');
		expect(content.querySelector('img')).toBeNull();
		expect(link?.getAttribute('href')).toBe('https://example.com/chart.png');
		expect(link?.getAttribute('target')).toBe('_blank');
		expect(link?.textContent).toContain('image: chart');
	});

	it('keeps a link title inside its own attribute', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: `[docs](https://example.com/docs.md 'say "hi" onmouseover="alert(1)"')\n` }
		});

		const link = getByTestId('markdown-content').querySelector('a');
		expect(link?.getAttribute('onmouseover')).toBeNull();
		expect(link?.getAttribute('title')).toBe('say "hi" onmouseover="alert(1)"');
	});

	it('keeps a link destination inside its own attribute', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: '[docs](<https://example.com/docs.md" onmouseover="alert(1)>)\n' }
		});

		const link = getByTestId('markdown-content').querySelector('a');
		expect(link).not.toBeNull();
		expect(link?.getAttribute('onmouseover')).toBeNull();
	});

	it('leaves a link whose code hides behind a tab as text', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: '[click me](<java\tscript:alert(1)>)\n' }
		});

		expect(getByTestId('markdown-content').querySelector('a')).toBeNull();
	});

	it('leaves a link whose code hides behind a control character as text', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: '[click me](<\u0001javascript:alert(1)>)\n' }
		});

		expect(getByTestId('markdown-content').querySelector('a')).toBeNull();
	});

	it('does not load an image the file carries inline', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: '![pixel](data:image/png;base64,AAAA)\n' }
		});

		expect(getByTestId('markdown-content').querySelector('img')).toBeNull();
	});

	it('keeps code blocks escaped rather than double-escaped', () => {
		const { getByTestId } = render(MarkdownRenderer, {
			props: { text: '```js\nconst a = 1 < 2 && 3 > 2;\n```\n' }
		});

		expect(getByTestId('markdown-content').textContent).toContain('const a = 1 < 2 && 3 > 2;');
	});
});
