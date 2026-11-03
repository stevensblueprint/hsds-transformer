# Evidence record

Use this compact shape; scale rows to the change. A proposed command starts as `NOT RUN`.

- Repository, base SHA, candidate SHA, and any dirty diff or patch hash.
- Environment/tool versions, fixture identifiers, and simulated boundaries.
- Expected behavior and selected risks.

| Check and expected result | Exact command or action | Status | Observed result and evidence | Limitation or next step |
| --- | --- | --- | --- | --- |
| One row per selected check | Include working directory | PASS / FAIL / NOT RUN | Output/log/capture path or CI run tied to this SHA | Explain failure, omitted coverage, or stale evidence |

`PASS` means the check ran and its stated expectation was observed. `FAIL` means an executed check failed; distinguish an expected old-revision reproduction from candidate failure. `NOT RUN` means no usable execution evidence, including blocked prerequisites or evidence from an earlier candidate. Preserve the earlier result in a note when marking it stale.

Report static, unit, integration, and end-to-end evidence at their actual scope. For a browser upload/download flow, a passing build proves buildability; an API-only test leaves browser behavior unverified. Inspect downloaded contents when transformation correctness is the claim.

After cleanup, check that artifact paths still resolve. Keep logs and captures free of secrets and private user data. State any unverified outcome plainly, along with the smallest next check that would resolve it.
