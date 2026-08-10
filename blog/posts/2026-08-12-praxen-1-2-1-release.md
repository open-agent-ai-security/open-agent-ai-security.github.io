---
title: Praxen 1.2.1: A Fast Follow — Clearer Reports, Sharper Docs, Hardened Pipeline
author: Steve Wilson
date: 2026-08-12
published: yes
summary: A fast-follow to Praxen 1.2 — polish for reports and docs, supply-chain hardening for how we ship, and a verification story about keeping the benchmark honest. Your scores don't move.
tags: release, praxen
image: praxen-1-2-1-release.png
image_alt: Praxen 1.2.1 release — clearer reports, sharper docs, hardened pipeline.
---

Last week we shipped [Praxen 1.2](../praxen-1-2-release/), aligned to the 2026 OWASP Top 10 for LLM Applications, and the community response has been great. Today's **Praxen 1.2.1** is the fast follow: everything we polished while 1.2 was landing in your hands.

The headline is what *doesn't* change: **your scores**. Nothing in 1.2.1 touches detection, scoring, or the analysis itself — reports you ran on 1.2 remain directly comparable to reports you run on 1.2.1. This is deliberate patch discipline: feature releases can move the measurement; patch releases never do.

## Clearer reports

Two small changes you'll notice the next time you open a report:

- **Every finding card now shows its confidence level.** Praxen has always assessed how confident it is in each finding — now that's visible right on the card, so you can weigh a tentative Medium differently from a rock-solid one.
- **Documentation links inside reports now land on the styled guides** — the same pages you'd browse on the Praxen site — instead of raw rendered Markdown. Every risk-tag chip and help link got the upgrade. Existing reports you've already generated keep working unchanged.

## Sharper docs

- **Upgrading from 1.1?** There's now a [dedicated callout in the installation guide](https://open-agent-ai-security.github.io/praxen/guide/installation.html) covering exactly what changes after the jump — the schema 3.0 findings format, the 2026 OWASP names, and why scores aren't comparable across the 1.1→1.2 boundary.
- **The scan-comparison tool is now documented.** Praxen 1.2 quietly shipped a scan-to-scan diff that shows what's new, resolved, or unchanged between two runs — 1.2.1 gives it the [documentation](https://open-agent-ai-security.github.io/praxen/guide/understanding-variability.html) it deserved.
- **Troubleshooting is one recipe, not three.** A scan that failed, went quiet, or produced a thin report now has a single re-run procedure instead of three separate diagnoses.
- A simplicity pass across the README, install, and quickstart docs — less jargon, faster to a first scan.

## Hardening how we ship

A verification tool has to hold itself to the standard it checks others against, so 1.2.1 invests in the supply chain behind Praxen itself:

- **Every GitHub Action in every workflow is now pinned to a full commit SHA**, not a movable version tag, with automation keeping the pins current.
- **Automated dependency merges now fail closed** — if branch protections aren't in place to gate them, they don't happen.
- **Contribution sign-off checks are tighter**, so automation identities can't be spoofed into skipping them.

None of this changes what you install — it changes how confidently we can stand behind what you install.

## Keeping the benchmark honest

One change deserves the full story. Praxen's skill instructions included worked examples that described a real agent from our public 12-agent benchmark — including two of its actual findings. That's a fairness problem waiting to happen: the instructions the scanner reads shouldn't contain advance knowledge about anything it might be asked to score.

In 1.2.1, those examples are rewritten around an invented agent that teaches the same lessons. And because we don't ship prose changes to the skill on faith, we gated it: a fresh, blind re-scan of the affected benchmark agent on the edited skill landed **exactly on its frozen published median** — and the finding the old examples had pre-described still surfaced on its own, as the top finding, from independent evidence. The benchmark stands, now with one less asterisk.

## Get 1.2.1

Already running Praxen? Two commands (the first refreshes the catalog so the second can see the new version):

**Claude Code**

```bash
claude plugin marketplace update open-agent-ai-security
claude plugin update praxen@open-agent-ai-security
```

**OpenAI Codex**

```bash
codex plugin marketplace upgrade open-agent-ai-security
codex plugin add praxen@open-agent-ai-security
```

New to Praxen? Install from the community marketplace:

```bash
claude plugin marketplace add open-agent-ai-security/plugins
claude plugin install praxen@open-agent-ai-security
```

Full instructions — including auto-update and the no-marketplace path for other coding agents — are in the [installation guide](https://open-agent-ai-security.github.io/praxen/guide/installation.html). The full change list is in the [CHANGELOG](https://github.com/open-agent-ai-security/praxen/blob/main/CHANGELOG.md), and the source, as always, is on [GitHub](https://github.com/open-agent-ai-security/praxen).

Run the update, keep scanning your agents, and keep telling us what you find.
