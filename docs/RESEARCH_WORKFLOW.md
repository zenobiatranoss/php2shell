# Research Workflow

## Objective

Keep vulnerability research reproducible and distinguish observed behavior
from assumptions about root cause or exploitability.

## Evidence collection

For each local lab run, record:

- PHP version and build configuration
- Relevant extensions and INI settings
- Test case identifier and exact reproduction steps
- Process exit status and HTTP response status
- Sanitizer output, when available
- Whether the result repeats across clean runs

Do not include access tokens, real session cookies, credentials, or
unrelated personal data in committed logs.

## Interpreting results

- An AddressSanitizer report is evidence of a memory-safety issue in that run.
- HTTP 500 and memory-limit errors indicate failures, not necessarily a
  specific root cause.
- Text resembling shell output is not independent proof of remote execution.
- A missing log pattern does not demonstrate that a bug is absent.

## Reproducibility

Run `make check` before recording a change.
Run `make analyze` to regenerate the local evidence report.
Review the report and relevant original logs together.

## Scope

Run experiments only in an isolated environment you control or are
explicitly authorized to test. Keep test results separate from claims that
have not been independently verified.
