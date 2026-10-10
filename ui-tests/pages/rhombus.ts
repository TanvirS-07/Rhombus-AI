import { Page, Locator, expect } from '@playwright/test';

// All selectors for the Rhombus AI app live here, so a UI change only needs a fix in one place.
export class RhombusApp {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  projectCard(name: string): Locator {
    return this.page.getByTestId('project-card').filter({ hasText: name });
  }

  node(nodeId: string): Locator {
    return this.page.getByTestId(`rf__node-${nodeId}`);
  }

  edge(from: string, to: string): Locator {
    return this.page.getByRole('button', { name: `Edge from ${from} to ${to}` });
  }

  get canvasTab(): Locator {
    return this.page.getByRole('tab', { name: 'Canvas' });
  }

  get previewTab(): Locator {
    return this.page.getByRole('tab', { name: 'Preview' });
  }

  get aiBuilderTab(): Locator {
    return this.page.getByRole('tab', { name: 'AI Builder' });
  }

  get runButton(): Locator {
    return this.page.getByTestId('run-pipeline');
  }

  async openProject(name: string) {
    await this.page.goto('/');
    const card = this.projectCard(name);
    await expect(card).toBeVisible();
    await card.click();
    await expect(this.runButton).toBeVisible({ timeout: 15_000 });
  }

  async openPreview(nodeId: string) {
    await this.node(nodeId).click();
    await this.previewTab.click();
  }
}
