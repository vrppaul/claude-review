import { describe, it, expect } from 'vitest';
import { ApiError, read } from '$lib/api/request';
import { endReview, imageUrl, keepImage, submitReview, takeDiff } from '$lib/api/review-api';
import { diffResponse } from './diff';
import { fakeServer, SERVER_ERROR, UNPROCESSABLE } from './fake-server';
import { screenshot } from './pasted-images';

/** A round with nothing in it, as the page would send one. */
const AN_EMPTY_ROUND = { threads: [], end: false };

/** What the page sees of a request that did not succeed. */
async function refusalOf(request: Promise<unknown>): Promise<ApiError> {
	const error = await request.then(
		() => null,
		(thrown: unknown) => thrown
	);
	if (!(error instanceof ApiError)) throw new Error(`Expected a refusal, got ${String(error)}`);
	return error;
}

describe('asking the server', () => {
	it('tells the reader why the server refused, in its own words', async () => {
		fakeServer().refuse('POST /api/submit', UNPROCESSABLE, 'The review has already ended');

		const refusal = await refusalOf(submitReview(AN_EMPTY_ROUND));

		expect(refusal.message).toBe('The review has already ended');
		expect(refusal.status).toBe(UNPROCESSABLE);
	});

	it('says what was being done, and the status, when the server gave no reason', async () => {
		fakeServer().fail('POST /api/submit', SERVER_ERROR);

		const refusal = await refusalOf(submitReview(AN_EMPTY_ROUND));

		expect(refusal.message).toBe(`Could not send the review: ${SERVER_ERROR}`);
	});

	it('names each field the server found wrong, and why, by its place in what was sent', async () => {
		fakeServer().refuseAsInvalid('POST /api/submit');

		const refusal = await refusalOf(submitReview(AN_EMPTY_ROUND));

		expect(refusal.message).toBe(
			'Could not send the review: threads.1.body: String should have at most 50000 characters; end: Field required'
		);
		expect(refusal.status).toBe(UNPROCESSABLE);
	});

	it('says in words what was being done when the request never reached the review', async () => {
		fakeServer().drop('POST /api/submit');

		const refusal = await refusalOf(submitReview(AN_EMPTY_ROUND));

		expect(refusal.message).toBe('Could not send the review: the review did not answer');
		expect(refusal.status).toBeNull();
	});

	it("names in the diff's query only what the reader changed: whitespace, and another base", async () => {
		const server = fakeServer();
		server.answer('GET /api/diff', diffResponse());

		await takeDiff({ ignoreWhitespace: false, base: null });
		await takeDiff({ ignoreWhitespace: true, base: 'round:2' });

		expect(server.requestsTo('GET /api/diff').map((request) => request.query)).toEqual([
			{},
			{ ignore_whitespace: 'true', base: 'round:2' }
		]);
	});

	it('says a no in a query as a no, and leaves out only what says nothing', async () => {
		const server = fakeServer();
		server.answer('GET /api/diff', diffResponse());

		await read('get', '/api/diff', { query: { ignore_whitespace: false, base: null }, doing: 'Taking the diff' });

		expect(server.requestsTo('GET /api/diff').map((request) => request.query)).toEqual([
			{ ignore_whitespace: 'false' }
		]);
	});

	it('sends an image as itself rather than wrapped in JSON', async () => {
		const server = fakeServer();
		server.answer('POST /api/images', { image_id: 'kept.png' });
		const image = screenshot();

		const kept = await keepImage(image);

		expect(kept.image_id).toBe('kept.png');
		expect(server.bodiesSentTo('POST /api/images')).toEqual([image]);
	});

	it('sends nothing to a route that takes nothing', async () => {
		const server = fakeServer();
		server.answer('POST /api/end', null);

		await endReview();

		expect(server.bodiesSentTo('POST /api/end')).toEqual([null]);
	});

	it('names an image in its path as the path can carry it, whatever the id holds', () => {
		expect(imageUrl('a b/c?d')).toBe('/api/images/a%20b%2Fc%3Fd');
	});
});
