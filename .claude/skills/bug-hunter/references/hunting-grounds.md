# Hunting grounds — where webapp bugs actually live

This is a map of failure shapes, not a checklist to run top to bottom. Read the sections for your territory, then go looking in the code. A pattern from this list is a reason to *investigate*, never a finding on its own — the finding is what you can prove about this codebase.

Contents:
1. [Entry points and authorization](#1-entry-points-and-authorization)
2. [Data and persistence](#2-data-and-persistence)
3. [Client state and data flow](#3-client-state-and-data-flow)
4. [The seam — client meets server](#4-the-seam--client-meets-server)
5. [Async, concurrency, and integrations](#5-async-concurrency-and-integrations)
6. [Cross-cutting: the things that hide everywhere](#6-cross-cutting)

---

## 1. Entry points and authorization

The premise: enumerate every route, handler, server action, resolver, webhook, and job, then check each one individually. Authorization bugs are almost never systemic — the system is fine and *one* endpoint out of forty is missing a line. Averages don't find that; enumeration does.

**Authentication vs authorization.** Being logged in is not permission. A handler behind an auth middleware that then loads a record by an ID from the request body, without checking the record belongs to the caller, is an IDOR — and it's the single most common serious webapp bug. Look for `findById(req.params.id)` with no ownership predicate.

**Tenant scoping applied N-1 times out of N.** In multi-tenant apps, look for the one query that filters by `id` where every sibling filters by `id AND org_id`. Also check the places scoping is easy to forget: aggregate and count queries, exports, search, admin endpoints, background jobs (no request context, so no tenant unless it's passed explicitly), and anything hitting a read replica or cache keyed without the tenant.

**Authorization in the wrong layer.** The UI hides the delete button; the endpoint doesn't check the role. Hiding a control is not enforcement. Whenever the client makes a permission decision, go find the corresponding server-side check and confirm it exists.

**Object-level vs route-level.** Route-level checks ("admins only") often pass while the object-level check ("this admin's org owns this record") is missing. Nested resources are where this bites: `/orgs/:orgId/projects/:projectId` where `projectId` is trusted and `orgId` is only used for the route match.

**Input validation.** Which fields are validated, which are trusted. Mass assignment — spreading a request body into an update where the model has `role`, `isAdmin`, `credits`, or `ownerId`. Coercion at boundaries: a query-string `"0"`, `"false"`, or `"null"` becoming a truthy string, or an array arriving where a scalar was assumed (`?id=1&id=2`). Numeric IDs parsed with `parseInt` and never checked for `NaN`.

**Injection, honestly assessed.** Modern ORMs parameterize; a template literal inside `prisma.$queryRaw` does not. Look for raw query builders, `sql` template escapes, dynamic `ORDER BY`/table names (which parameterization can't cover), shell invocation with user input, path joins with user-supplied filenames, and SSRF where a user-supplied URL gets fetched server-side. Confirm the input reaches the sink before reporting.

**Also:** enumeration and error-message leakage (different responses for "no such user" vs "wrong password"), missing rate limits on login/reset/OTP/expensive endpoints, secrets or internal errors serialized into responses, CORS with credentials plus reflected origin, state-changing `GET`s, file uploads without type/size limits, and redirect targets taken from user input.

---

## 2. Data and persistence

**Nullability as the database defines it, not as the types claim.** Read the migrations and the schema, not just the model classes. A column nullable in the DB but non-optional in the generated type produces a runtime crash the type system swears is impossible. Same for columns added in a later migration with no backfill: every row written before it is null regardless of what the schema says now.

**Transactions.** Multi-step writes that must be atomic but aren't — the classic is create-record-then-charge-card, or two updates that must agree. Check whether the ORM's transaction wrapper is actually awaited and whether the inner calls use the transaction handle rather than the global connection (a very common silent bug: the code looks transactional and isn't). Check what happens on partial failure, and whether an error inside the transaction triggers a rollback or is caught and swallowed.

**Lost updates.** Read-modify-write with no optimistic locking, version column, or conditional update. Two concurrent requests both read `balance: 100`, both write `90`, one update vanishes. Counters, inventory, balances, and status transitions are where this hurts. `UPDATE ... SET x = x - 1` is safe; `x = read(); write(x - 1)` is not.

**Check-then-act.** "Does this email exist? No → insert." Under concurrency both checks pass. The fix is a unique constraint; the bug is the absence of one. Look for uniqueness enforced only in application code.

**N+1.** A list endpoint that loads N records and then loops issuing a query per record — through a lazy-loaded relation, an `await` inside `.map`, a resolver without a dataloader, or a helper that looks pure and hits the database. Confirm the loop is over a collection that grows with data, not a fixed three-element array; unbounded is the bug.

**Missing indexes on the filters that actually run**, unbounded queries with no limit, `SELECT *` pulling blobs into list views, and offset pagination over a large, mutating table (which both slows down and skips rows as data shifts).

**Migrations.** Non-additive changes deployed against running old code (dropping or renaming a column the previous version still writes), migrations that lock a large table, backfills without batching, and defaults that only apply to new rows.

**Also:** money in floats instead of integer minor units or decimal, timestamps stored without timezone, `DATE` vs `DATETIME` truncation, enum values in the database that the application enum no longer has, cascade deletes that reach further than intended (and the reverse — orphans with no cascade and no cleanup), soft deletes that half the queries forget to filter, and JSON columns read with assumptions about a shape nothing enforces.

---

## 3. Client state and data flow

**Effects and their dependencies.** Missing dependencies capture stale values; over-broad dependencies loop. An effect that fetches on every render because a dependency is an object or array literal recreated each time is a real bug — it hammers the server and can produce flicker or infinite loops.

**Race conditions in fetching.** User types fast, or navigates; response 1 arrives after response 2 and overwrites newer data with older. Look for `fetch` in an effect with no abort signal, no request-sequence guard, and no cleanup. Same shape: setting state after unmount.

**Optimistic updates without rollback.** The UI applies the change immediately, the request fails, and nothing reverts. The user believes the write succeeded. Check every optimistic path for its error branch, and check that the error branch restores the *previous* value rather than refetching-and-hoping.

**Cache invalidation after mutation.** A mutation succeeds and the list it affects isn't invalidated, so the user sees stale data and reports it as "the save didn't work". In React Query/SWR terms: mutations with no `invalidateQueries`, or invalidating a key that doesn't match the one the list uses. Also over-broad keys that share a cache entry across different tenants or users — a genuine data-leak class in SPAs.

**Error states that render as success.** A component with a loading state and a success state but no error state shows an empty list forever when the request 500s. Similar: `catch` blocks that log and return `null`/`[]`, so the failure is indistinguishable from "no data".

**Forms.** Double submit because the button isn't disabled while in flight — this is how duplicate orders happen. Validation only client-side. Uncontrolled-to-controlled transitions. State reset on a re-render that loses typed input. Files uploaded without progress or failure handling.

**Also:** `key` on list items derived from array index while the list reorders or filters, event listeners/intervals/observers added without cleanup, `localStorage` holding data that must not survive logout, secrets in client bundles or `NEXT_PUBLIC_`-style variables, `dangerouslySetInnerHTML` with anything user-derived, and derived state duplicated into `useState` and left to drift from its source.

---

## 4. The seam — client meets server

This is the territory no per-file review covers, and where the costly bugs concentrate. The technique is always the same: take a server response shape and follow it into the client, or take a client assumption and go verify it against the handler.

**Contract drift.** Hand-written client types that no longer match the handler. A field renamed on the server, added, made nullable, or moved into a nested object, with the client's TypeScript still asserting the old shape — the compiler is happy because nothing validates at the boundary. Check a few high-traffic endpoints field by field against the type the client uses. If types are generated from a spec, check the spec is regenerated in CI and not just committed by hand.

**The error path.** The happy path is usually tested; the error path is usually assumed. What does the handler return on failure — a 200 with `{error}`, a 4xx with a JSON body, a 500 with an HTML error page? Does the client check `res.ok` before `res.json()` (a plain `fetch` doesn't throw on 4xx/5xx — a very common bug), and does it handle a body that isn't JSON? Does a validation error surface a usable message or a generic "something went wrong" that hides the actual problem?

**Serialization.** JSON has no date type and no decimal type. Dates cross as strings and get parsed in the browser's local timezone, shifting a day near midnight. `Decimal`/`BigDecimal`/`money` types serialize as strings or floats and get arithmetic done on them in JS, where `0.1 + 0.2` is not `0.3`. 64-bit integer IDs exceed `Number.MAX_SAFE_INTEGER` and silently lose precision. Look for any of these types crossing the boundary and check what the client does with them.

**Pagination and filtering split across the boundary.** The API returns the first 100 rows; the client filters, sorts, or counts them and presents the result as complete. Totals computed client-side over a truncated page are simply wrong. Also: server-side search that ignores a filter the UI shows, so the user's filter appears to do nothing.

**Authorization assumed on the wrong side.** Covered in §1 from the server's angle; from the client's angle, look for any UI conditional on a role or permission and go confirm the endpoint enforces the same rule. Also endpoints that return more fields than the UI displays — hidden in the UI, fully present in the network response.

**Also:** enum values the server can send and the client's switch doesn't handle (falling through to a blank screen); status codes the client doesn't distinguish (401 vs 403 — retrying a login on a permission error); required-vs-optional mismatches in request bodies; content-type mismatches on upload; and a client retrying non-idempotent `POST`s.

---

## 5. Async, concurrency, and integrations

**Unhandled rejections and floating promises.** An `async` call without `await` and without `.catch` — the work continues, the failure vanishes, and the response returns as if it succeeded. In an `Array.map` with async callbacks and no `Promise.all`, the results are promises and the code proceeds with them as if they were values. In .NET the same shape is an un-awaited `Task` or `async void`.

**Retries without idempotency.** A retry on a `POST` that creates a record, charges a card, or sends an email, with no idempotency key and no dedupe. Retries at multiple layers compound: client retries, gateway retries, queue redelivery — check whether the consumer is safe to run twice, because at-least-once delivery guarantees it eventually will.

**Webhooks.** Signature verification present and actually enforced (not verified-then-ignored). Replay protection. Out-of-order delivery — webhooks arrive in the wrong sequence and the handler applies them blindly, so a `cancelled` event lands before `created`. Non-2xx responses causing redelivery of work already done.

**Background jobs.** No request context means no tenant, no user, no locale — check what the job assumes. Jobs holding a database transaction open across a network call. No timeout, so a hung external call blocks a worker forever. Failure handling: does a failed job retry forever, dead-letter, or disappear silently?

**External calls.** Missing timeouts (the default in many HTTP clients is none). No circuit breaker on a dependency that will eventually be down. Errors from a third party mapped to a 500 that tells the user nothing. Rate limits from the provider unhandled.

**Resource leaks.** Connections, file handles, streams, subscriptions, and listeners acquired and not released on the error path — the success path closes them, the `throw` skips the close. Unbounded in-memory caches and maps keyed by user or session that nothing evicts.

**Also:** `Promise.all` where one rejection discards the other results that mattered, `await` inside a loop that should be concurrent (slow rather than wrong, but reportable when it's a user-facing latency problem), sequential dependent writes with no compensation on partial failure, and shared mutable module-level state in a server process where every request touches the same object.

---

## 6. Cross-cutting

Things that show up in any territory and are worth a deliberate pass:

- **Swallowed errors.** `catch {}`, `catch { log }` then continue, `except: pass`, `catch (e) { return null }`. Each one is a place where a failure becomes invisible. Judge by consequence: swallowing a logging failure is fine, swallowing a write failure is not.
- **Off-by-one and boundaries.** Slice and range arithmetic, inclusive/exclusive date ranges, `>=` vs `>` on limits and quotas, pagination edges, empty-collection handling.
- **Time.** Timezone assumed to be the server's, "today" computed in the wrong zone, DST arithmetic done by adding 24 hours, expiry compared against a clock that can drift, timestamps generated on the client.
- **The comment that disagrees with the code.** A doc comment or TODO describing behavior the code no longer has is a strong signal that one of the two changed and its counterpart didn't.
- **Copy-paste divergence.** Five handlers written from the same template and one missing a line. Diffing siblings against each other is one of the highest-yield techniques available — it's how the single unscoped query gets found.
- **The version-specific.** Behavior that depends on the framework version in use. Verify the version before claiming a framework bug or a missing framework protection; guessing here is a reliable way to manufacture a false positive.
