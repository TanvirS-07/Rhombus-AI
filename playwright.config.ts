import { defineConfig } from '@playwright/test';
import 'dotenv/config';
import fs from 'fs';

export default defineConfig({
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'api',
      testDir: './api-tests',
      use: { baseURL: process.env.RHOMBUS_API_BASE_URL || 'https://api.rhombusai.com/api/' },
    },
    {
      name: 'ui',
      testDir: './ui-tests',
      use: {
        baseURL: process.env.RHOMBUS_APP_URL || 'https://rhombusai.com',
        browserName: 'chromium',
        // The canvas only draws nodes inside the window, so use a large window to fit the whole pipeline.
        viewport: { width: 1920, height: 1080 },
        storageState: fs.existsSync('.auth/user.json') ? '.auth/user.json' : undefined,
      },
    },
  ],
});
