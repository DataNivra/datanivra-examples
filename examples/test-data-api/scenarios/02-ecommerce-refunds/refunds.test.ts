/**
 * E-commerce refunds — Vitest suite that acquires approved test data before the tests and always releases it.
 * DataNivra provisions data into the approved target; your tests use their own database access.
 */
import { readFileSync } from 'node:fs';
import type { TestDataRequest } from '@datanivra/contracts';
import { createDataNivraClient } from '@datanivra/sdk';
import { TestDataClient } from '@datanivra/sdk/testdata';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

const api = createDataNivraClient({
  baseUrl: process.env.DATANIVRA_BASE_URL ?? 'https://api.example.test',
  getAccessToken: () => process.env.DATANIVRA_TOKEN,
});
const testData = new TestDataClient(api);
let request: TestDataRequest | undefined;

beforeAll(async () => {
  const manifest = readFileSync(new URL('./request.yaml', import.meta.url), 'utf8');
  const created = await testData.request(manifest, { idempotencyKey: process.env.CI_RUN_KEY });
  request = await testData.wait(created.id, { timeoutMs: 600_000 });
}, 660_000);

afterAll(async () => {
  if (request) await testData.release(request.id, 'TEST_RUN_FINISHED');
});

describe('refunds', () => {
  it('runs against approved, certified test data', () => {
    expect(request?.state).toBe('READY');
    // assert refunds never exceed the captured amount
  });
});
