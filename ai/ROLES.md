# Roles

Specialist roles that review or test this project. **This file is a catalog, not loaded every session.**
Each role is defined once (a role skill, ideally in the personal skill library) and can run two ways:

- **Inline:** a working agent launches it as a subagent with the role skill when a trigger hits
  (e.g. "this change touches auth" -> security auditor). Gets the context of the current change.
- **Scheduled:** a runner (cron, CI, the agents server) checks out the repo and runs the same role skill on a
  cadence. Gets independence and the whole repo. Skips the run if nothing changed since its last run.

Every role **reports** (issue or PR, with severity and evidence; never edits `AGENTS.md` directly) and remembers
what it already reported. Only safe mechanical fixes (formatting, dependency bumps) come as PRs.
Tools first, LLM for judgment. Model tier: **L** local/cheap model is enough, **M** mid, **S** strong model needed.

Run `/roles` right after `/kickoff` to trim this catalog to what THIS project needs. Default for every
role is `dropped`; a role becomes `active` only with a concrete reason.

## Active roles (filled by `/roles`)

| Role | Why this project needs it (concrete risk or goal) | Focus (paths, features) | Inline trigger | Schedule | Output |
|---|---|---|---|---|---|
| | | | | | |

## Catalog

Status: `candidate` (not yet reviewed) / `active` / `dropped` (with reason) / `later` (with the condition).

### Code quality and correctness
| Role | Mission | Relevant when | Tools first | Tier | Status |
|---|---|---|---|---|---|
| Tester | Missing tests for changed behaviour; flaky tests | Always, once there is code | test runner, coverage | M | candidate |
| E2E / QA tester | User journeys still work end to end | Has a UI or API used by people | Playwright, API tests | M | candidate |
| Bug hunter | Reachable defects, adversarially verified (`bug-hunter`) | Non-trivial app logic | the skill's Hunter/Skeptic/Referee | S | candidate |
| Clean coder | Code health: duplication, dead code, complexity, naming | Codebase grows past a few modules | linters, complexity metrics | M | candidate |
| Architect | Boundaries, dependencies, decisions vs ADRs | Several modules/services; long-lived | dependency graph, arch tests | S | candidate |
| Performance engineer | Slow paths, N+1, bundle size, memory | Users wait on it, or it costs compute | profilers, benchmarks, Lighthouse | M | candidate |
| Stress tester | Behaviour under load, limits, breaking point | Expected concurrency or traffic spikes | k6, Locust | M | candidate |
| Spec keeper | Spec vs code drift (what's built vs what's specified) | Spec-driven project | `sdlc-build-status` | M | candidate |

### Security and compliance
| Role | Mission | Relevant when | Tools first | Tier | Status |
|---|---|---|---|---|---|
| Security auditor | Vulnerabilities in code and config (auth, injection, secrets) | Any deployed or networked code | Semgrep, CodeQL, gitleaks | S | candidate |
| Ethical hacker | Attacks the running system, own environments only, explicit scope | Deployed app with users or data | OWASP ZAP, Burp (sandboxed) | S | candidate |
| Dependency warden | Vulnerable / abandoned / unpinned dependencies | Any third-party packages | pip-audit, npm audit, Renovate | L | candidate |
| License auditor | Licence compatibility of dependencies | Distributed or commercial product | license checkers | L | candidate |
| Privacy officer | PII handling, retention, GDPR | Stores personal data | data-flow map, PII scanners | S | candidate |

### Product, UX and content
| Role | Mission | Relevant when | Tools first | Tier | Status |
|---|---|---|---|---|---|
| UI designer | Visual consistency, design system, states (empty/loading/error) | Has a UI | screenshots, design tokens | S | candidate |
| UX reviewer | Usability of key flows, friction, confusing copy | Has users doing tasks | journey walkthroughs | S | candidate |
| Accessibility auditor | WCAG issues | Public or enterprise UI | axe, Lighthouse a11y | M | candidate |
| Copywriter | Clarity and tone of user-facing text | User-facing text matters | readability checks | M | candidate |
| i18n reviewer | Hard-coded strings, locale formats | Multiple languages/regions | i18n linters | L | candidate |
| Product owner | Features vs goal and metric; scope creep | Has a product goal | `AGENTS.md` goal, issue tracker | S | candidate |

### Growth
| Role | Mission | Relevant when | Tools first | Tier | Status |
|---|---|---|---|---|---|
| SEO engineer | Indexability, metadata, structured data, Core Web Vitals | Public website | Lighthouse, sitemap/robots checks | L | candidate |
| Marketer | Positioning, landing copy, competitor changes | Product needs users | web research | M | candidate |
| Analytics engineer | Tracking plan vs what is actually tracked | Decisions depend on usage data | event schema checks | M | candidate |

### Operations
| Role | Mission | Relevant when | Tools first | Tier | Status |
|---|---|---|---|---|---|
| CI keeper | Failing/flaky CI, slow pipelines | Has CI | CI logs | L | candidate |
| SRE / observability | Errors in logs, missing alerts, health checks | Runs in production | log queries, uptime checks | M | candidate |
| Cost watcher | Cloud and LLM spend vs budget | Pays for infra or tokens | billing APIs, `hooks/finops/` | L | candidate |
| Release manager | Changelog, versioning, release readiness | Ships versions to others | git tags, changelog | L | candidate |
| Data quality | Freshness, nulls, duplicates, schema drift | Has data pipelines | dbt tests, Great Expectations | M | candidate |
| AI eval engineer | Prompt/model regressions on a fixed eval set | Contains LLM features | eval harness, LLM-as-judge | S | candidate |

### Knowledge
| Role | Mission | Relevant when | Tools first | Tier | Status |
|---|---|---|---|---|---|
| Context keeper | `AGENTS.md` accurate and short; promotes durable findings from role reports | Always | git log, role reports | M | candidate |
| Docs writer | README/setup docs work for a newcomer | Others will use or run it | follow the docs from scratch | M | candidate |
| Issue triager | Labels, duplicates, stale issues, severity | Issue tracker in use | tracker API | L | candidate |

## Added for this project (not in the catalog)
| Role | Mission | Why | Tools first | Tier |
|---|---|---|---|---|
