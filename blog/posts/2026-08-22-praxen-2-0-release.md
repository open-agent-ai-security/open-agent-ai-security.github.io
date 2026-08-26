---
title: Praxen 2.0: Threat Modeling, Drawn from the Code Itself
author: Steve Wilson
date: 2026-08-22
published: no
summary: Praxen 2.0 turns an agent's own code into a live, visual threat model — trust boundaries, STRIDE threats, and attack paths you can follow by hovering, with every element citing file:line evidence.
tags: release, praxen
image: praxen-2-0-release.png
image_alt: Praxy the fox tracing a glowing red attack path across a holographic architecture diagram, next to Praxen 2.0 Threat Modeling.
---

Today we're releasing **[Praxen](https://open-agent-ai-security.github.io/praxen/) 2.0** — the biggest release since the project launched.

Praxen shipped in late June with one idea: verify what an AI agent *actually does* against what its policy *says it does*, and show the receipts. Since then the releases have come fast — a 12-agent public benchmark, OWASP Top 10 tagging, thinking modes that put a skeptical reviewer inside every scan, and scores rebuilt so each number traces to evidence on disk. Along the way the project picked up press coverage, real users, and real bug reports from real deployments.

2.0 adds the thing those users kept asking for, and the thing agent security most badly lacks: **the architecture view**. Not a whiteboard drawing from a meeting six months ago — a threat model **derived from the agent's own code**, rendered as a diagram you can interrogate, where every box, boundary, and threat cites file:line evidence.

## Threat modeling is urgent again

Threat modeling used to be something you did once, on a whiteboard, for a system that changed twice a year. Agents broke that model. An AI agent's attack surface shifts every time someone adds a tool, connects an MCP server, or edits a prompt — and the people asked to secure these systems are often meeting the architecture for the first time. The classic disciplines still apply — trust boundaries, STRIDE, data-flow analysis — but nobody has time to hand-draw them for a system that changed last Tuesday.

So Praxen draws it. Ask for a threat model and a fresh extraction pass reads the agent's workspace — entry points, orchestrator, prompts, model calls, memory, tools, deploy artifacts, and the controls meant to guard them — and builds the model the way a security architect would, if the architect had read every file:

- **Components in five trust lanes** — user inputs → clients and adapters → agent core → tools and MCP → external and deploy — so the diagram reads left to right the way trust degrades.
- **Trust boundaries** drawn where the crossings actually happen, each carrying its threats named in **STRIDE** and **OWASP** language.
- **Attack paths** that run from an untrusted origin to a consequence — host shell, data egress, a poisoned memory — where every step is a real edge in the graph, citing the finding that proves it.
- A plain-English executive summary up top: what the agent is, and which threats to deal with first.

## Hover a target. See exactly how you get owned.

![Hovering a target in the FinBot threat model isolates the attack paths that reach it — everything else fades](praxen-2-0-target-isolation.gif)

The report is not a static picture. Targets — the places where damage lands — wear a red badge. **Hover one, and the diagram mutes everything except the attack path(s) that reach it**: the untrusted origin where the attacker gets in, the controls the path slips past, the hop where injected content becomes an action, and the consequence — lit end to end, flowing red, in isolation. Every other node fades. The question a security review actually asks — *this thing here, how does an attacker reach it?* — is answered by pointing at it.

The rest of the report works the same way: click any component to jump to its inventory row and evidence, click a boundary badge for its threat table, hover any flow for its citation. And the model is honest about roles — when a disclosure path ends where it began (a crafted message that gets the agent's own instructions read back to the attacker), the caller's node wears both badges: source *and* target. That is exactly the kind of path a whiteboard session never draws.

## Receipts, as always

A Praxen threat model is built *on top of* a completed analysis, and it shows its work:

- A threat is **confirmed** only when a scan finding proves it in code. No finding, no confirmed — the model never invents evidence.
- Threats the top-down view raises that the scan never examined surface as **potential** — which is precisely the review list your next pass should start from.
- The extraction is **score-inert**: it never changes a finding, a score, or the analysis report. It's a second lens on the same evidence, validated against a published graph contract before a single pixel renders.

In our testing, independent extractions of the same target converged on the same trust-boundary set and threat statuses, with variation confined to enumeration depth and naming at the margins.

> "Every security team I talk to is being asked to sign off on agents they've never seen an architecture diagram for. 2.0 draws that diagram from the code itself — and when a CISO asks 'how would an attacker reach the booking system?', you hover the booking system and the answer lights up."
>
> — Steve Wilson, lead maintainer of Praxen

## All twelve benchmark targets, threat-modeled, live now

We didn't ship a feature and a promise. Every target in Praxen's public 12-agent benchmark ships with a hosted threat model today, linked beside its analysis report and remit on the [suite health page](https://open-agent-ai-security.github.io/praxen/tests/baselines/suite-health-report.html). Browse them like a gallery of agent security architecture: [OpenHands](https://open-agent-ai-security.github.io/praxen/tests/baselines/v1.3-opus5/openhands/openhands-threatmodel-2026-08-21-143615.html), the autonomous software engineer; [Hermes](https://open-agent-ai-security.github.io/praxen/tests/baselines/v1.3-opus5/hermes-agent-desktop/hermes-agent-desktop-threatmodel-2026-08-21-143615.html), a desktop assistant reachable from two dozen chat platforms; [OpenAI's customer-service demo](https://open-agent-ai-security.github.io/praxen/tests/baselines/v1.3-opus5/openai-customer-service/openai-customer-service-threatmodel-2026-08-21-143615.html), anonymous caller to booking write. Three very different agents; the same five lanes; very different attack stories.

## What it costs

In our testing — twenty measured extractions across the gate runs and the full benchmark sweep — a threat model runs roughly **0.5–1× the tokens of a standard scan, typically ~0.75×**, in one fresh-context pass of about 10–20 minutes. It's opt-in, invoked in plain language: *"Run a Praxen threat model"* after an analysis, or *"run a Praxen analysis with a threat model"* to do both in one go.

## Also in 2.0

- The threat model links back to the analysis report it was built against, straight from its masthead
- The x-high adjudicator now receives the raw runs' evidence-checkpoint paths explicitly (closing a spec gap found in review — the validation runs had already done the right thing)
- Thinking-mode costs in the docs now quote the measured figures throughout
- The diagram fits a laptop screen — five lanes, no horizontal scrolling

## Get Praxen 2.0

Praxen 2.0 installs from the Open Agent AI Security community marketplace.

**Claude Code**

```bash
claude plugin marketplace add open-agent-ai-security/plugins
claude plugin install praxen@open-agent-ai-security
```

**OpenAI Codex**

```bash
codex plugin marketplace add open-agent-ai-security/plugins
codex plugin add praxen@open-agent-ai-security
```

Then point it at an agent and say *"run a Praxen analysis with a threat model."* Full instructions are in the [installation guide](https://open-agent-ai-security.github.io/praxen/guide/installation.html); the methodology — STRIDE, the boundary archetypes, how attack paths are proven — is in the new [threat modeling guides](https://open-agent-ai-security.github.io/praxen/guide/threat-modeling.html); the source lives on [GitHub](https://github.com/open-agent-ai-security/praxen).

Hover a target. See what reaches it. Then fix the path, not just the finding.
