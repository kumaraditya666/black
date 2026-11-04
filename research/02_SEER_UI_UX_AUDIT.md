# Public Seer UX audit

Research date: 2026-11-04. Evidence labels distinguish direct observation, source statements, and recommendations. Product claims are vendor claims, not independently validated performance.

## Information architecture

**CONFIRMED — observed:** Chrome DevTools opened [Seer's public product page](https://sentry.io/product/seer/) in an isolated context. Its accessibility snapshot exposes a main navigation menu, a primary headline, free signup and sandbox links, two embedded interactive product demonstrations, feature links for Agent, Autofix and AI Code Review, use cases, FAQs, and footer navigation. An issue-fix demo advertises four steps and an Agent demo seven. These are marketing and scripted demos, not a live authenticated product observation.

**CONFIRMED — documented:** [Issue details](https://docs.sentry.io/product/issues/issue-details/) describe a Seer section, stack trace, issue activity, tags, linked issues, and release information. The [experimental fix-state API](https://docs.sentry.io/api/seer/retrieve-seer-issue-fix-state/) documents progress, root cause, proposed solution, code changes, repository permissions and run state. Its example is documentation, not a captured live investigation.

**UNKNOWN:** authenticated issue layout, actual visual code viewer, exact design tokens, responsive breakpoints, keyboard operability of the complete product, loading and failure states. Do not infer production design from marketing embeds. No visual token sampling or full accessibility audit was performed.

## UX hypotheses for independent design

- **HYPOTHESIS:** Separate observation, inference and missing evidence visually; link every causal claim to exact telemetry and code revision. This could help users assess unsupported claims; user studies are needed.
- **HYPOTHESIS:** Provide an onboarding checklist explaining instrumentation, repository access and expected data gaps. Validate with first-time users before claiming reduced friction.
- **HYPOTHESIS:** A dependency map is useful only when nodes and edges expose provenance, freshness and navigation to relevant signals; otherwise a searchable list may be clearer.
- **HYPOTHESIS:** Show proposed patch, tests actually run, reproduction status and approval action separately, avoiding a single misleading “fixed” label.

The snapshot confirms a skip link, headings, labeled controls, and embedded demos with accessible region labels; it does not establish WCAG compliance, color contrast, keyboard reachability or screen-reader usability. Our own visual system should be original.
