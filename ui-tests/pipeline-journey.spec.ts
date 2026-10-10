import { test, expect } from '@playwright/test';
import fs from 'fs';
import { RhombusApp } from './pages/rhombus';

const projectName = process.env.RHOMBUS_PROJECT_NAME;
const authFile = '.auth/user.json';

// Node ids on the canvas, in pipeline order (see observations/baseline.md).
const nodeIds = [
  'input_node_1',
  'text_cleanup_node_1',
  'remove_duplicate_node_1',
  'remove_duplicate_node_2',
  'llm_node_1',
  'output_node_1',
];

const outputColumns = [
  'order_id',
  'customer_name',
  'email',
  'country',
  'order_date',
  'quantity',
  'amount_usd',
  'status',
];

test.describe('Rhombus AI pipeline journey', () => {
  test.beforeEach(async () => {
    test.skip(!fs.existsSync(authFile), `Log in once to create ${authFile} (see README)`);
    test.skip(!projectName, 'Set RHOMBUS_PROJECT_NAME in .env');
  });

  test('opens the project and shows the full pipeline on the canvas', async ({ page }) => {
    const app = new RhombusApp(page);

    await app.openProject(projectName!);

    // Each step must be connected to the next one, in order.
    for (let i = 0; i < nodeIds.length - 1; i++) {
      await expect(app.edge(nodeIds[i], nodeIds[i + 1])).toBeAttached();
    }
    await expect(app.node('llm_node_1')).toBeVisible();
  });

  test('preview of the cleaned data shows the 8 output columns', async ({ page }) => {
    const app = new RhombusApp(page);

    await app.openProject(projectName!);
    await app.openPreview('llm_node_1');

    for (const column of outputColumns) {
      await expect(page.getByText(column, { exact: true }).first()).toBeVisible();
    }
    await expect(page.getByText('70.84', { exact: true }).first()).toBeVisible();
  });

  test('running the pipeline starts a job that finishes successfully', async ({ page }) => {
    test.setTimeout(180_000);
    const app = new RhombusApp(page);

    await app.openProject(projectName!);

    const started = page.waitForResponse(
      (res) => res.url().includes('/pipeline/process') && res.request().method() === 'POST',
    );
    const finished = page.waitForResponse(
      async (res) => {
        if (!res.url().includes('/background_jobs/jobs/') || res.status() !== 200) return false;
        const body = await res.json().catch(() => null);
        return body?.status === 'SUCCESS' || body?.status === 'FAILED';
      },
      { timeout: 170_000 },
    );

    await app.runButton.click();

    const startRes = await started;
    expect(startRes.status()).toBe(200);
    expect((await startRes.json()).message).toContain('started');

    const job = await (await finished).json();
    expect(job.status).toBe('SUCCESS');
  });
});
