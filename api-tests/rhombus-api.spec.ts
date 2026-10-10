import { test, expect, APIRequestContext } from '@playwright/test';

const token = process.env.RHOMBUS_API_TOKEN;
const orgId = process.env.RHOMBUS_ORG_ID;
const projectId = process.env.RHOMBUS_PROJECT_ID;
const projectName = process.env.RHOMBUS_PROJECT_NAME;

// The pipeline built by the AI builder, in order (see observations/baseline.md).
const expectedNodes = [
  'orders_raw',
  'orders_trimmed',
  'orders_no_exact_dups',
  'orders_deduped',
  'orders_cleaned',
  'orders_output',
];

function headers(authToken?: string): Record<string, string> {
  const h: Record<string, string> = { accept: 'application/json' };
  if (orgId) h['x-org-id'] = orgId;
  if (authToken) h['authorization'] = `Bearer ${authToken}`;
  return h;
}

async function getProjects(request: APIRequestContext, authToken?: string) {
  return request.get('dataset/projects/all', {
    params: { limit: 1000, offset: 0 },
    headers: headers(authToken),
  });
}

test.describe('Rhombus AI API', () => {
  test('lists projects and includes the drift test project', async ({ request }) => {
    test.skip(!token || !projectName, 'Set RHOMBUS_API_TOKEN and RHOMBUS_PROJECT_NAME in .env');

    const res = await getProjects(request, token);

    expect(res.status()).toBe(200);
    expect(res.headers()['content-type']).toContain('application/json');
    const body = await res.json();
    expect(body.total).toBeGreaterThan(0);
    const names = body.items.map((p: { name: string }) => p.name);
    expect(names).toContain(projectName);
  });

  test('returns the pipeline nodes in the expected order', async ({ request }) => {
    test.skip(!token || !projectId, 'Set RHOMBUS_API_TOKEN and RHOMBUS_PROJECT_ID in .env');

    const res = await request.get(`dataset/analyzer/v2/projects/${projectId}/nodes`, {
      headers: headers(token),
    });

    expect(res.status()).toBe(200);
    const nodes = await res.json();
    const tags = nodes.map((n: { metadata?: { result_tag?: string } }) => n.metadata?.result_tag);
    expect(tags).toEqual(expectedNodes);
  });

  test('negative: rejects a request with no token', async ({ request }) => {
    test.skip(!projectName, 'Set RHOMBUS_PROJECT_NAME in .env');

    const res = await getProjects(request);

    expect([401, 403]).toContain(res.status());
    expect(await res.text()).not.toContain(projectName);
  });

  test('negative: rejects a fake token', async ({ request }) => {
    test.skip(!projectName, 'Set RHOMBUS_PROJECT_NAME in .env');

    const res = await getProjects(request, 'not-a-real-token');

    expect([401, 403]).toContain(res.status());
    expect(await res.text()).not.toContain(projectName);
  });

  test('negative: unknown project returns a client error, not a server error', async ({ request }) => {
    test.skip(!token, 'Set RHOMBUS_API_TOKEN in .env');

    const res = await request.get('dataset/analyzer/v2/projects/999999999/nodes', {
      headers: headers(token),
    });

    expect([403, 404]).toContain(res.status());
  });
});
