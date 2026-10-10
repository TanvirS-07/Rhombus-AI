import { defineConfig } from '@playwright/test';
import 'dotenv/config';

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
      use: { baseURL: process.env.RHOMBUS_APP_URL || 'https://rhombusai.com' },
    },
  ],
});
