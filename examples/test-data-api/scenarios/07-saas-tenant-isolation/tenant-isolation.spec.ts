/**
 * SaaS tenant isolation — Playwright test using approved test data. The browser exercises your application;
 * DataNivra only provisioned the data behind it (metadata flows through this file, never rows).
 */
import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';
import { createDataNivraClient } from '@datanivra/sdk';
import { TestDataClient } from '@datanivra/sdk/testdata';

const api = createDataNivraClient({
  baseUrl: process.env.DATANIVRA_BASE_URL ?? 'https://api.example.test',
  getAccessToken: () => process.env.DATANIVRA_TOKEN,
});

test('one tenant never sees records of another tenant', async ({ page }) => {
  const manifest = readFileSync(new URL('./request.yaml', import.meta.url), 'utf8');
  await new TestDataClient(api).withTestData(
    manifest,
    async (request) => {
      expect(request.state).toBe('READY');
      await page.goto(process.env.APP_URL ?? 'http://localhost:3000');
      // sign in as two synthetic tenants and assert neither list shows the other's ids
    },
    { idempotencyKey: process.env.CI_RUN_KEY },
  );
});
