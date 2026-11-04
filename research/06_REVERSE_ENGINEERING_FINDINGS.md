# Targeted inspection findings

Research date 2026-11-04. This section describes permitted public observations and documentation, not private Sentry implementation. No binaries were downloaded or executed for this investigation, and REA was not used for target inspection. Browser inspection was carried out with Chrome DevTools MCP. REA availability was checked independently by the parent research stream.

## 1. Public page embeds separate demo origins

**CONFIRMED — observation:** the page accessibility tree lists interactive demos loaded in separate `demo.arcade.software` iframes. Browser network metadata showed the public iframe documents returning 200. **Method:** Chrome DevTools snapshot and bounded request listing. **Why it matters:** an embedded demonstration can present a safe, scripted journey separately from marketing navigation. **Unknown:** internal state and whether screenshots are live product data. **Independent implementation:** a product tour may use representative, explicitly labeled sample data; avoid presenting it as actual user telemetry. [Page](https://sentry.io/product/seer/).

## 2. Public state representation

**CONFIRMED — documentation:** Sentry's experimental [state endpoint](https://docs.sentry.io/api/seer/retrieve-seer-issue-fix-state/) documents status, steps, progress messages, repository access and code-change fields. **Method:** official public API documentation, including its illustrative response. **Why it matters:** state and evidence can be represented separately from a final narrative. **Unknown:** internal storage, orchestration, model prompts, timing, and guarantees. **Independent implementation:** persist immutable run events with versioned artifacts and scoped permissions; this is a proposal, not a claim about Sentry's internals.

## 3. Explicit staged API

**CONFIRMED — documentation:** [start issue fix](https://docs.sentry.io/api/seer/start-seer-issue-fix/) describes an asynchronous run with selectable steps and stopping points. **Why it matters:** a client can render progress and place consent at side-effect boundaries. **Unknown:** backend worker topology or whether proposed changes are actually tested. **Independent implementation:** model typed states and enforce approved transitions; treat proposed action and executed action as separate records.

## Limitations

No client-side JavaScript bundles were decompiled, no authenticated workflow or private endpoint was inspected, and no hidden backend mechanism is claimed. A review of source code or another public artifact may justify deeper targeted REA use later; no unnecessary invasive inspection was performed.
