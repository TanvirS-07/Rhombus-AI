# Rhombus AI: Pipeline Testing Under Schema and Semantic Drift

This repository is my submission for the Rhombus AI Software Engineer Intern take-home. I built a cleaning pipeline in Rhombus AI that reads an orders file from S3 and writes the cleaned result to GCS, then tested how the pipeline, its logs and its chatbot behave when the source data changes.

- Demo video: [YouTube Video Link](https://youtu.be/Ub3u_5v1KGU)
- Dashboard: https://tanvirs-07.github.io/Rhombus-AI/ (published from `dashboard/` by GitHub Pages)

## Repository structure

- `datasets/`: the baseline orders file and one file per drift test, all created by `generate.py`
- `pipeline/`: the prompt used to build the cleaning pipeline in the AI builder
- `runs/`: every output downloaded from GCS, one folder per test
- `data-validation/`: the validator (`validate.py`), the output contract, a reference cleaner and a report for every test in `reports/`
- `observations/`: one write-up per test, evidence (error messages and chatbot answers) and usability notes
- `api-tests/`: Playwright API tests against the Rhombus API
- `ui-tests/`: Playwright UI tests for the main pipeline journey
- `dashboard/`: a static page that summarises the results

## Setup

Requirements: Node 18 or later and Python 3.10 or later.

```bash
npm install
npx playwright install chromium
```

### API tests

1. Copy `.env.example` to `.env`.
2. Sign in to Rhombus AI in a browser, open DevTools, go to the Network tab and select any request to `api.rhombusai.com`.
3. Copy the bearer token from the `Authorization` header into `RHOMBUS_API_TOKEN`, and the `x-org-id` header into `RHOMBUS_ORG_ID`.
4. Set `RHOMBUS_PROJECT_ID` and `RHOMBUS_PROJECT_NAME` to your own project.

The token expires, so it needs to be copied again if the tests start returning 401.

```bash
npm run test:api
```

There are 5 tests: 2 positive (the project list includes the project, and the pipeline nodes come back in the expected order) and 3 negative (no token, an invalid token, and a project that does not exist).

### UI tests

Rhombus sign-in uses a one-time email code, so the UI tests reuse a saved session instead of logging in each time. Save it once:

```bash
npx playwright codegen --save-storage=.auth/user.json https://rhombusai.com
```

Sign in in the window that opens, then close it. The session in `.auth/user.json` is ignored by git and expires after a while, so repeat this step if the UI tests are skipped or redirected to the login page.

```bash
npm run test:ui
npx playwright test --project=ui --headed
```

There are 3 tests: the canvas shows the 5 connections between the pipeline nodes, the Preview tab shows the cleaned columns and values, and pressing Run starts a job that finishes with SUCCESS. If `.auth/user.json` is missing, the UI tests are skipped rather than failing.

### Data validation

The validator has no third-party dependencies (pytest is only needed for its own tests).

```bash
python data-validation/validate.py --case baseline --input datasets/orders_baseline.csv --output runs/baseline/run1.csv
python data-validation/run_all.py
```

`run_all.py` validates every folder in `runs/` and writes the reports to `data-validation/reports/`. Each check compares the output against the contract in `contract.json` and against a reference cleaner, and also looks for semantic problems such as dates outside the expected window or amounts at the wrong scale.

## Observations

Each test has its own write-up in `observations/`, with the steps to repeat it, the error message, the chatbot's answers, the outputs and the validator report. The baseline write-up covers building the pipeline.

Severity follows the scale in the brief: Critical means bad data reached GCS with a success status and no warning, High means the run broke and the logs or chatbot did not help, Medium means the change was handled but the message was confusing, and Low means it was handled well.

| Drift test | Pipeline stopped? | Chatbot fix worked? | Validation caught it? | Severity |
|---|---|---|---|---|
| [Drop column](observations/schema-drop-column.md) | Yes, failed | Only for the drifted file; it broke the original file | Yes | High |
| [Rename column](observations/schema-rename-column.md) | Yes, failed | No, then yes after I named the rename | Yes | High |
| [Type change](observations/schema-type-change.md) | Yes, with a misleading error | No (an empty file reached GCS), then yes after I named the change | Yes | High |
| [Add column](observations/schema-add-column.md) | No, output correct | Not needed | Yes, flagged the new column | Low |
| [Combined schema changes](observations/schema-combined.md) | Yes, failed | No in two rounds, then yes after a hint | Yes | High |
| [Amounts in cents](observations/semantic-cents.md) | No, wrong amounts written silently | Yes after a hint, but it broke the original file | Yes | High |
| [Dates as DD/MM](observations/semantic-date-ddmm.md) | No, 14 wrong dates written silently | No, two claimed fixes changed nothing | Yes, all 14 rows | Critical |

The [baseline](observations/baseline.md) took 6 outputs to get right, and every incorrect output was reported as a successful run.

## Top 3 findings

1. Day and month were swapped silently, and the chatbot claimed fixes that did nothing. When dates arrived as DD/MM, the pipeline read them as MM/DD and wrote 14 wrong dates to GCS with a success status. The chatbot first said the dates were correct. Its two fixes produced a byte-identical output, and the second one described a cause that did not exist and said the fix was "verified in simulation". A downstream user would have no way to tell anything was wrong. ([details](observations/semantic-date-ddmm.md))

2. Chatbot fixes often only work for the file in front of them, or turn a failure into silent bad data. In the type change test the first fix removed the crash and an empty file reached GCS. In the drop column and cents tests the fix worked for the drifted file but broke the original one, so restoring the original source gave wrong output. In most cases the chatbot only found the real cause after I described it myself.

3. Run status cannot be trusted as a signal of data quality, and the scheduler hides changes. Every wrong output in this project was reported as a success. Scheduled runs skipped changed source files as "unchanged data", so every drift test had to be run by hand, and successful scheduled runs do not appear in the logs at all.

## Usability feedback

The AI builder makes it quick to get a pipeline that looks reasonable, and the canvas and Preview tab make each step easy to inspect. Adding a column was handled cleanly, and once the pipeline was correct it gave the same output on every run. The difficulty is everything after the first draft. It took 6 outputs and 7 follow-up messages to reach a correct baseline, and the platform never warned about any of the wrong outputs.

When something does fail, the error message is a dump of generated Python rather than a sentence about the data, and the chatbot tends to report a fix as done without checking the result. I would suggest showing a short plain-language cause with the column and rows affected, rerunning a fix against both the old and the new file before calling it done, and letting users add simple output checks (row count, date range, value scale) that stop a run before it writes to GCS. The full list is in [observations/usability-notes.md](observations/usability-notes.md).

## Notes on secrets

`.env`, `.auth/`, HAR files and any `*-key.json` files are listed in `.gitignore`. No tokens, passwords or cloud keys are committed.
