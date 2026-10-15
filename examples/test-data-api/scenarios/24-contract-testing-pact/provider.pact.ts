/**
 * Consumer/provider contract testing — Pact provider verification with approved test data.
 * Illustrative: @pact-foundation/pact is not a dependency of this repository.
 */
import { readFileSync } from 'node:fs';
import { Verifier } from '@pact-foundation/pact';
import { createDataNivraClient } from '@datanivra/sdk';
import { TestDataClient } from '@datanivra/sdk/testdata';

const testData = new TestDataClient(
  createDataNivraClient({
    baseUrl: process.env.DATANIVRA_BASE_URL ?? 'https://api.example.test',
    getAccessToken: () => process.env.DATANIVRA_TOKEN,
  }),
);

await testData.withTestData(
  readFileSync(new URL('./request.yaml', import.meta.url), 'utf8'),
  async () => {
    await new Verifier({
      providerBaseUrl: process.env.PROVIDER_URL ?? 'http://localhost:8080',
      pactUrls: ['./pacts/web-orders.json'],
    }).verifyProvider();
  },
);
