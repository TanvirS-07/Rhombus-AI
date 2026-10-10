# Usability notes

Bugs and UI improvements I noticed while building the pipeline and running the drift tests. Each one links to the test where it came up.

## Setting up the pipeline

1. **The third-party connector is hard to find.** It took me a while to find where to connect S3, because the "Third party sources" option is not obvious in the data input menu.
2. **The "Third Party Data: Connection details" panel cannot be scrolled.** Part of the form can end up out of view.
3. **The AI builder created a node it could not run.** One LLM node was saved with an empty prompt and the pipeline failed until I asked for it to be fixed (`baseline.md`).
4. **A default text cleanup step stripped decimal points, minus signs, `@` and apostrophes.** Amounts became 100x too large and emails were blanked, and the run still showed success (`baseline.md`).

## Running and scheduling

5. **Successful scheduled runs do not appear in the logs.** A scheduled run wrote a file to GCS, but the Rhombus logs and UI showed no record of it. I could only confirm it by looking in the bucket (`baseline.md`).
6. **The scheduler does not pick up a changed source file.** After I uploaded a new `orders.csv` to S3, scheduled runs kept skipping with "unchanged data" for 30 minutes or more. Only a manual Run read the new file (`schema-drop-column.md`).
7. **The Data Input preview shows a stored copy of the file.** The node preview showed the old file while the dataset view (eye icon) showed the new one, which made it hard to tell which file the pipeline would use (`schema-drop-column.md`).
8. **Errors are shown as a dump of generated code.** The useful part (for example `KeyError: 'country'`) is buried after the code, and none of the errors said in plain words that a column was missing or had changed type (`schema-drop-column.md`, `schema-type-change.md`).
9. **An empty output file is treated as a success.** In the type change test, every row was dropped and a file with only the header was written to GCS. The only sign was a small note on one node (`schema-type-change.md`).

## The chatbot

10. **It reports fixes that did not change anything.** This happened in the baseline build and twice in the DD/MM test, where it also said it had "verified in simulation" that the dates were correct (`semantic-date-ddmm.md`).
11. **Its fixes often only fit the file in front of it.** Removing `country`, skipping missing columns and dividing every amount by 100 all broke the original file or hid later problems (`schema-drop-column.md`, `schema-rename-column.md`, `semantic-cents.md`).
12. **It does not check output values, only formats.** When asked whether anything looked wrong, it called the cents output "largely correct" and the DD/MM output "correct" (`semantic-cents.md`, `semantic-date-ddmm.md`).
13. **"Ask Chatbot" can repeat the same answer.** In the combined test it re-locked the same code twice and blamed the scheduler, even though both runs were manual (`schema-combined.md`).

## What worked well

- Connecting the GCS destination worked the first time.
- Setting a schedule was easy to find and change.
- Once given a precise hint, the chatbot usually produced a correct fix quickly, and some fixes (dates as Unix timestamps, the combined schema) kept the original file working too.
- The pipeline picks columns by name, so an extra column or a change in column order did not break it (`schema-add-column.md`).
