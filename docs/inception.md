# Perch — inception.md

**Project name:** Perch (package / repo: `perchwall`)

A design-history and handoff document for **Perch**, a personal **authenticated element-screenshot dashboard**. This captures the full arc of the design conversation: the original problem, every option considered, what was decided, what was rejected and *why*, and the current agreed-upon design. It is written to hand to another LLM (or future-self) to begin implementation planning. Nothing here is code; it is intent, decisions, and rationale.

**Name rationale & availability:** "Perch" = the spot you survey from; the tool is a wall of glances at pages you're already logged into. Chosen over Mosaic (crowded; react-mosaic is a tiling-window-manager — an uncomfortable conceptual neighbour), Vantage (live cloud-cost SaaS brand in an adjacent space), and Snip (saturated in dev tooling). Bare `perch` is taken on PyPI and npm and the word appears in an old PHP "Perch CMS", so the package/repo is qualified as **`perchwall`**, which was verified greenfield: free on PyPI, free on npm, no real GitHub repo-name matches, and the GitHub handle/org `perchwall` is free. (Note: `perchboard` was rejected — an active ★51 project of the same "personal home dashboard" category already exists.) **Domains (`perchwall.dev/.app/.com/.io`) were NOT verified** — check in a real registrar before relying on one.

---

## 1. The problem

The user holds several paid subscriptions to web services (originally framed as LLM subscriptions — Claude, OpenCode, Minimax, Cursor, "and more"). Each service exposes **usage / limit / expiry information only on an authenticated settings web page**. There is no API access to these figures for subscription accounts.

The goal: **collect all of these usage views into one place — a single web page / dashboard** — with a way to refresh them on demand.

Key early clarifications from the user:

- The **styling of each meter can differ**. Visual consistency across tiles is explicitly *not* required. An image (or iframe) per meter is acceptable.
- They want them **in one place**.
- They want to **click a button to refresh / refetch the latest**, and (initially) optionally auto-refresh. Auto-refresh and scheduling were later dropped (see §7).

---

## 2. Why the obvious approaches don't work

### 2.1 APIs
The usage/limit data is not available via API for subscription accounts. This is the founding constraint — it forces everything into the "read the authenticated web page somehow" space.

### 2.2 iframes (rejected for the important cases)
The user suggested iframes as a simple embed. **This does not work for the key services.** Claude, Cursor, and Minimax send `X-Frame-Options: DENY` or a restrictive `frame-ancestors` Content-Security-Policy, so their pages refuse to render inside a third-party `<iframe>` — the result is a blank box. iframes remain viable only for pages that *permit* framing (some self-hosted / public pages), so they cannot be the general mechanism.

### 2.3 CLI clients (investigated, rejected as a general mechanism)
The user asked whether the figures could all be fetched via the services' CLI clients. Investigated per-service:

- **Claude** — has a CLI (Claude Code) with a `/usage` view, but it reports Claude Code plan usage, not necessarily the same meters as web account settings. No clean "print my limits as JSON" command. **Partial at best.**
- **OpenCode (Go)** — is itself a CLI, but it is a *client* that talks to whatever model provider is configured. It has no own-subscription usage endpoint. "Usage" for OpenCode is really the backing provider's usage. **Nothing meaningful to fetch.**
- **Cursor** — no official usage CLI. Usage lives in the dashboard web page (and an internal authenticated endpoint the page calls). **No supported CLI path.**
- **Minimax** — API-platform usage is queryable *with an API key*, but the subscription meters on the web settings page are not exposed as a clean CLI command.

**Conclusion:** CLIs are inconsistent, partial, and in OpenCode's case not even a coherent concept. They cannot be the uniform mechanism; relying on them would leave several empty tiles. A CLI collector may still be a *per-target option* for any source where a command genuinely returns real data, but it is not the backbone.

---

## 3. The reframe that shaped everything: this is not LLM-specific

A pivotal realization: once the LLM framing is stripped away, the tool is a **generic authenticated element-screenshot dashboard**. It logs into arbitrary sites, captures specific DOM elements, and tiles them. The LLM services are just the first entries in a config file.

Consequences of the reframe (all adopted):

- The core abstraction is a list of things to capture; nothing in the engine knows or cares that any given entry is an LLM tool.
- Adding a new thing (GCP billing page, a home-server admin panel, a Grafana panel, a portfolio widget, a status page, etc.) is **just another config entry — no code change.**
- It solves a broader problem than APIs: many useful things have no API, or a gated/paid API while the web page is right there behind an existing session. Screenshotting an element sidesteps all of it uniformly — "if you can see it in a browser, you can put it on the wall."

This reframe also drove the **terminology change** (see §8): the word "provider" was dropped as too LLM-flavored.

---

## 4. Capture mechanism: how we land on screenshots

### 4.1 Screenshots vs DOM+CSS capture
The user proposed capturing the **actual DOM plus the CSS needed** for each element instead of a screenshot (for crisp, selectable, rescalable content). This was explored in depth:

- **Option A — outerHTML + all stylesheets (naive):** easy but captures the entire site's CSS, breaks on selectors/ancestors that no longer exist once the element is plucked out, and inherited layout context is lost. Usually ~70% right.
- **Option B — computed-style inlining:** walk the subtree, resolve `getComputedStyle` per node, write values as inline styles. Robust against missing ancestors because values are pre-resolved. Verbose; snapshots one state; pseudo-elements and background images need special handling. The "sweet spot" for static meters.
- **Option C — CDP snapshot / MHTML:** most faithful, least code, but captures the *whole page* not a clipped element.
- **The cross-cutting snag — assets:** background images, web fonts, SVG icons, CSS custom properties on `:root`. Inlined computed styles capture resolved colour/size but `url(...)` assets 404 outside the session and fonts fall back. Fixable by inlining assets as base64 data URIs, at more effort.

The best DOM-capture variant identified: **computed-style inlining on just the meter element, background-images/SVGs inlined as data URIs, each tile wrapped in a shadow DOM** to prevent cross-source CSS bleed.

**Decision: go with screenshots, not DOM capture.** Rationale: given the user's explicit tolerance for differing styles, screenshots "just work" across every service including the framing-blocked ones, need no per-service CSS/asset fiddling, and are dramatically less code. DOM capture is crisper and selectable but more code, more per-service fragility, and still needs selector maintenance. Screenshots' one real cost — they're fixed-resolution pixels — is acceptable here.

### 4.2 Element-clipped screenshots, and controlling size
Confirmed capabilities that make screenshots viable and small:

- **Element-only capture:** Playwright's `locator.screenshot()` captures just that element's bounding box (auto-scrolls it into view). No cropping math. Caveats: disambiguate multi-match selectors (`.first` or a more specific selector); if the element is inside an `overflow`-clipping parent, screenshot the parent instead. A manual `clip` rect on `page.screenshot()` is a fallback.
- **Viewport size** (`new_context(viewport={...})`) mostly controls *layout*, not final image size — the element screenshot is only as big as the element renders. Narrow viewports can trigger responsive/mobile layouts (sometimes desirably compact; sometimes hides the element behind a hamburger menu — so viewport width is a per-target layout lever).
- **`device_scale_factor`** is the real knob for sharpness/filesize: `2` = retina-crisp/bigger, `1` or below = smaller. Capture sharp, then constrain **display** size with CSS (`img { max-width: ... }`) independently.

---

## 5. Driving the browser: Playwright, CDP, extensions, Firefox

### 5.1 The core fork: reuse the real session, or run a separate automated one?
Normal Playwright/Puppeteer launch their *own* browser with their *own* profile → you must log in again inside that automated browser and keep those sessions alive. That re-login is the main ongoing pain. Everything below is about how to handle it.

### 5.2 Options considered
1. **Browser extension** (runs inside the real logged-in browser; zero separate auth). Uses `chrome.tabs.captureVisibleTab()` / Firefox `tabs.captureTab()` with a `rect` clip, or Chromium's `chrome.debugger` (CDP) for clipped capture. **Rejected** (see §5.4).
2. **Lightweight CDP, no Playwright** — launch Chrome with `--remote-debugging-port` (even the real profile) and drive it with `chrome-remote-interface` / `pychrome`. Lighter than Playwright, real sessions, but more manual work and a debug port open on the daily browser.
3. **Playwright over CDP (`connect_over_cdp`)** to an existing Chrome — keeps Playwright's nice API *and* real sessions.
4. **Puppeteer** — only meaningfully lighter if already Node-first and using system Chrome (`puppeteer-core`). Not worth switching.

### 5.3 Firefox reality (the user mostly uses Firefox)
**CDP is a Chromium protocol.** Firefox only ever had partial CDP support and Mozilla has been *removing* it in favour of the cross-browser **WebDriver BiDi** standard. So "attach to my real Firefox over a debugging port and drive it with CDP" is **not viable**. Bridges:

- **Playwright** abstracts over the protocol (drives Firefox via its own patched build + BiDi), giving the same `locator.screenshot()` API regardless of engine — but Playwright's Firefox is a *bundled, patched* Firefox, so "reuse my real logged-in Firefox session" is not the easy path there.
- **Use a separate Chromium for the collector** even though the user daily-drives Firefox. The collector browser is a headless background worker; it need not be the browsing browser. This **decouples "my browsing" from "the dashboard's browsing"** — arguably cleaner — at the cost of maintaining those logins separately.

### 5.4 Extension: feasible cross-browser, but rejected
- A single WebExtensions (MV3) codebase can target Firefox + Chromium with minor manifest differences, so a cross-browser extension is feasible.
- **Screenshot capability diverges:** Chromium has `captureVisibleTab` + `chrome.debugger`; Firefox has `captureVisibleTab`/`captureTab` with a `rect` clip but **no `chrome.debugger` equivalent**. So two capture paths, and Firefox's are the more standard ones.
- **The disruption problem:** capture generally requires the target tab to be *active/visible*. Screenshotting five background pages means bringing each tab to the foreground, stealing focus, "strobing" through tabs on every refresh. Softenable by using a separate minimized window, but MV3 killed the truly-invisible background-page tricks and `captureVisibleTab` fundamentally wants a visible tab.
- **Decision: no extension.** The disruption, the cross-browser capture quirks, and being bound to one machine's browser outweigh the free-auth benefit — especially since the user is fine logging in twice.

### 5.5 Decision
**Headless collector using a separate, persistent Chromium profile, driven by Playwright.** The user's Firefox usage stops mattering because the collector is its own isolated browser. Zero disruption (renders/screenshots entirely offscreen — no tab flicker, no focus theft). The accepted tradeoff is maintaining a separate set of logins (the user explicitly accepted "logging in twice"). Runs **on localhost only, not remote** (see §7) — this simplifies the security story.

---

## 6. Login & authentication mechanism

**The insight: you don't log into a headless browser — headless is only for capturing. Login is a one-time interactive step in *headed* mode, same browser, same profile.**

Mechanism — a **persistent user-data directory** (`launch_persistent_context(user_data_dir=...)`), which stores cookies/localStorage/session tokens on disk like a real profile. Log in once (headed); every later headless run reuses the directory already authenticated. Sessions last as long as the service's cookies do (often weeks); re-login only on expiry.

Two modes (one script with a `--login` flag, or two scripts):

- **Login mode — headed, interactive:** launch persistent context with `headless=False`, navigate to the page, **pause** (e.g. `input("...press Enter when logged in")`) so the human can log in by hand — including MFA / OAuth / captcha, because a human is doing it — then close; cookies are saved to the profile dir.
- **Capture mode — headless:** same `user_data_dir`, `headless=True`, already authenticated, navigate + `locator.screenshot()`.

Practical wrinkles noted:
- **Headless detection:** some sites treat headless Chromium differently (extra bot checks). Since login is headed and only *capture* is headless, this is mostly avoided; fixes if a capture page misbehaves headless: use `headless="new"` (real Chrome headless, less detectable) or fall back to headed-but-offscreen for that one source.
- **Where login runs:** originally a concern for a headless remote box (interactive login needs a display), but this is now **moot — the tool runs on localhost**, where a display is available for the one-time headed login.
- **Profiles are sensitive:** the directories contain live session tokens ("logged in as you"). Treat like credentials; the user Syncthings between machines, so **be deliberate about excluding the profiles dir from sync** (or accept "logged in as you" on every synced machine). Localhost-only operation reduces but does not remove this concern.

---

## 7. Scope decisions (explicit non-goals)

Deliberate scope cuts made during the conversation, to be recorded as **non-goals** so they aren't accidentally regrown:

- **No scheduling / no background auto-scrape.** Dropped. Refresh is on-demand only.
- **No auto-refresh loop hammering sources.** Initially floated (once-a-minute); dropped. Note: a page-side image refresh (re-requesting cached PNGs with a cache-busting `?t=` param) is cheap, but that only shows new pixels if a re-scrape happened. The two "clocks" (cheap image re-request vs expensive page re-load) must not be conflated. Frequent authenticated re-loads are exactly what risks account flagging — see §9.
- **Screenshots, not DOM+CSS capture** (see §4.1).
- **Localhost only, not remote.** (Earlier discussion assumed a Tailscale-accessible remote box; this was revised to localhost.)
- **No extension** (see §5.4).
- **CDP-against-Firefox** approach rejected (see §5.3).

Probably out of scope but flagged for a conscious yes/no by the implementer:
- **History / usage-over-time:** screenshots cannot provide this; it would require real data extraction — a different tool. Almost certainly a **no**.

---

## 8. Terminology (post-reframe, adopted)

"Provider" was **dropped** as too LLM-specific. The neutral model:

- **Source** = a web page to capture from. Has a URL and *optional* auth.
- **Target** (aka capture / clip) = a specific element on a source, identified by a selector. A tile in the dashboard renders one target.

Hierarchy: **source → one-or-more targets.** This natively supports **multiple meters per page** (a user requirement): e.g. Cursor is one source with two targets (usage meter, billing card).

**Auth is an optional property of a source, not a baseline.** Not every page has a login (public pages, LAN-local Grafana with anonymous access, status pages, weather). A source is either `auth: none` (plain stateless context, faster, no profile dir) or uses a named profile (the §6 persistent-context login flow). `--login` and login-required detection apply **only** to authenticated sources.

Efficiency payoff of the split: for a source with multiple targets, **load the page once and take multiple element screenshots** from that single load. Refresh iterates sources (page loads); within each, iterates targets (clips).

Illustrative config shape (not final — for orientation):

```yaml
sources:
  - name: cursor
    url: https://cursor.com/settings
    auth: { profile: cursor }        # or  auth: none
    ready: <optional wait rule>
    targets:
      - name: cursor-usage
        selector: "[data-testid='usage']"
      - name: cursor-billing
        selector: ".billing-card"
  - name: home-grafana
    url: http://192.168.1.50:3000/d/abc
    auth: none                        # public / LAN, no login
    targets:
      - name: cpu-panel
        selector: "..."
```

---

## 9. DOM targeting — how an element is addressed and how a user creates it

### 9.1 What the "address" is
A **CSS selector** (used ~95% of the time — same syntax as a stylesheet: `#id`, `.class`, `[data-testid="..."]`) or an **XPath** (fallback for what CSS can't express, mainly selecting by text content — `//button[contains(text(),"Usage")]` — or complex parent traversal). Playwright speaks both, and adds higher-level locators that target *meaning* not structure: `get_by_text(...)`, `get_by_role("progressbar")` — often more robust. A target's "where" is just a selector string in config.

### 9.2 Brittleness — the central maintenance risk
Modern SPA sites (Cursor, Claude, etc. are React apps) emit generated class names like `css-1x7ab3q` that change every deploy. Durable targeting, best → worst:
1. **`data-testid` / `id`** — stable, semantic, survive redesigns. Best when present.
2. **ARIA roles / text** — `get_by_role("progressbar")`, `get_by_text("Monthly usage")` — resilient to CSS churn.
3. **Structural CSS** — `.settings main > div:nth-child(3)` — works, fragile, breaks on layout shifts.
4. **Generated classes** — avoid; break on next deploy.

### 9.3 How a user creates a selector — three tiers
1. **Browser devtools (free, works today):** right-click element → Inspect → Copy → Copy selector / Copy XPath → paste into config. Downside: browsers often copy the *fragile* `nth-child`/generated-class kind; may need hand-tidying.
2. **Point-and-click picker (best UX, chosen to build):** during headed setup mode, inject a content script that highlights the element under the cursor and, on click, computes a selector and writes it into config automatically. Buildable in Playwright via `page.expose_function(...)` + injected JS that outlines on hover and calls back on click. Turns "add a tile" into "log in, click the thing, done" — no devtools, no YAML hand-editing. This is the feature that makes the tool feel finished.
3. **Smart selector generation:** the picker's on-click logic prefers `data-testid` → `id` → role+text → structural fallback, emitting the shortest *unique robust* selector. Libraries exist (`finder`, `optimal-select`).

**Decision:** build the **click-to-pick overlay** into setup mode, with robust-selector generation. It's a natural fit because setup already opens a headed, logged-in window — letting the user click the meter right there to define the target is the obvious move. The picker works **per-source**: in one setup pass the user can pick *multiple* elements (meter one, meter two), each becoming a target under that source.

---

## 10. Hardening / things that will bite if unplanned

These do not change the core architecture; they are the reliability layer. **The first three are considered must-haves from day one** — they are what separate "a dashboard I trust" from "a wall of maybe-stale images."

1. **Capture readiness ("did the number even load")** — *must-have.* SPA dashboards commonly return an element that exists but still shows a skeleton/spinner/`0`. `goto` + fixed `sleep` is fragile. Wait for the specific condition: `locator.wait_for(state="visible")` **plus** the element containing non-empty/non-zero text, and/or `wait_for_load_state("networkidle")`. Budget for a **per-target readiness rule** in config — "element exists" ≠ "element has real data."
2. **Timestamp + stale/error state per tile** — *must-have.* On failure (expired session, rotted selector, redesign), a silently-served stale PNG makes the dashboard lie. Each tile carries a **capture timestamp** ("captured 3m ago") and a visible **error/stale** state.
3. **Login-required detection** — *must-have* (for auth sources). Cookies expire; the failure mode is a capture that "succeeds" but screenshots a *login page*. After navigating, assert you're **not** on a login URL and that the target selector is present; if it fails, surface "re-login needed for &lt;source&gt;" and route the user back to the `--login` step for that profile — rather than screenshotting a login form.
4. **Concurrency on refresh-all** — for 4–5 sources, **sequential** capture is probably fine and much simpler (refresh-all takes ~15–30s; the UI should show per-tile "loading", not freeze). Parallel is faster but 5 concurrent Chromium contexts is real RAM, and parallel logins to SSO-shared domains can race.
5. **Concurrent refresh collisions** — overlapping refreshes (refresh-all + a per-tile refresh mid-flight) can open the same profile dir twice; Playwright persistent contexts dislike that. **Lock per source (or per profile)**, or use a small job queue. Refresh logic should **key on sources, not tiles**, so two tiles sharing a source don't double-load it.
6. **Screenshot dimensions drift** — the element's size can change between captures (responsive reflow, extra line, promo banner), making tiles jump. Decide: pin display size in CSS (capture varies, display fixed, accept letterboxing) vs organic tiles.
7. **Selectors will still rot** — even robust selectors break on big redesigns. The **recovery loop matters more than the happy path**: if re-picking is "run setup mode, click the thing, done," breakage is a 30-second fix and the tool survives; if it's "hand-edit YAML and guess," it bit-rots and gets abandoned. Design the recovery path.
8. **State / storage format** — a flat folder of PNGs **plus a small JSON or SQLite index** (timestamp, last status, selector, target config) is plenty. Decide it's the single source of truth up front so the dashboard reads from one place.

---

## 11. Legal / ToS note (sober, not alarmist)

Automating one's own authenticated dashboards is **grey-area** for most services; aggressive or frequent captures are what draw attention. Because scheduling is dropped and the tool is **manual-refresh, localhost, low-frequency, human-paced**, the risk profile is about as low as it gets. **Do not** later bolt on a 60-second auto-refresh loop hammering five services — that is the thing that gets accounts flagged. Keep it on-demand.

---

## 12. Inspiration (use ideas, do not build on)

Self-hosted dashboard engines were surveyed: **Glance, Dashy, Homarr, Homepage**. Glance in particular (tiny, fast, single binary / small Docker image, YAML config, iframe + custom-HTML + custom-API widgets, mobile-optimized) has appealing config-driven ergonomics. **Decision: do not build on Glance**, but borrow ideas (YAML config model, tile grid, mobile layout). Reasons it can't be the tool as-is: its iframe widget hits the same framing-block wall (§2.2), and it does not auto-refresh (a full page reload is needed; fetches on load then caches) — though the latter is moot given the on-demand decision. Hosted screenshot-API SaaS (ScreenshotAPI, urlbox, etc.) do offer element-clip + cookie-injection auth, but they are **rejected**: handing authenticated session cookies to a third party is a hard no. The self-hosted equivalent is "run Playwright yourself" — which is the chosen path.

**The gap this tool fills:** nobody ships a turnkey product combining (a) the user's *real authenticated session*, (b) *element-clipped* capture, and (c) a *tiled dashboard with manual refresh* — precisely because the auth piece is user-specific and legally grey, so open projects avoid baking it in. That gap is the reason to build rather than adopt.

---

## 13. Current agreed design (where we left off)

A **localhost, on-demand, config-driven screenshot dashboard**:

- **Collector:** Playwright driving a **separate, persistent-profile Chromium**, **headless for capture**, **headed only for one-time login** (`--login <source>`). Per authenticated source, a persistent `user_data_dir`. Public sources use `auth: none` (no profile). **Load each source once, clip many targets** from that load.
- **Config model:** `sources → targets`. A source = URL + optional auth (`none` or named profile) + optional readiness rule. A target = a selector (+ its name). Multiple targets per source supported.
- **Setup mode:** headed browser; log in if the source is authed; then a **click-to-pick overlay** where hovering highlights elements and clicking computes a **robust selector** (testid → id → role+text → structural fallback) and writes a new target into config. Multiple picks per session.
- **Reliability layer (must-haves): capture-readiness waiting; per-target timestamp + stale/error state; login-required detection** for authed sources. Plus: per-source locking, sequential refresh for 4–5 sources, PNG folder + JSON/SQLite index as single source of truth.
- **Front end:** a **tile grid** rendering targets (Glance-*inspired*, not Glance-built), with **manual refresh-all and per-source refresh** (refresh keyed on sources to avoid double-loading shared pages), and visible per-tile timestamp/stale/error/"re-login needed" states. Capture sharp (via `device_scale_factor`), display size constrained by CSS.

**Recommended reference targets for a first implementation:** **Cursor** as an authenticated source with **two meters** (usage + billing) to exercise the multi-target-per-source path, plus **one public / LAN source** (e.g. a local Grafana panel or a status page) to exercise the `auth: none` path.

**Open threads / decisions left to the implementer:**
- Shared single profile vs one profile per authenticated source. Leaning: **try a single shared profile first**; split only sources that misbehave (overlapping cookie domains / shared SSO like `accounts.google.com` can tangle sessions or cause cross-logout). It's a config detail, not an architectural fork.
- Sequential vs parallel refresh (leaning sequential for 4–5).
- Tile size: pinned-CSS vs organic.
- Storage index: flat JSON vs SQLite.
- Language/stack for the server: a small FastAPI service (with `/refresh` and `/refresh/<source>` style routes) was assumed throughout, but not locked.
- Explicit **no** recommended on usage-over-time history (would require data extraction, not screenshots).
