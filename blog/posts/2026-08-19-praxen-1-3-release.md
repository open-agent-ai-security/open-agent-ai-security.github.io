---
title: Praxen 1.3: Thinking Modes, and Scores Rebuilt from Evidence
author: Steve Wilson
date: 2026-08-19
published: yes
summary: Praxen 1.3 adds opt-in high and x-high thinking modes that catch what a single scan misses, and rebuilds RAISE scoring so every score traces to evidence on disk.
tags: release, praxen
image: praxen-1-3-release.png
image_alt: Praxy the fox deep in thought at a holographic screen, thinking mode set to extra hard, next to Praxen 1.3 Thinking Modes.
---

Today we're releasing **[Praxen](https://open-agent-ai-security.github.io/praxen/) 1.3**. It improves the two things that matter most in an agent security review: how much a scan finds, and how much you can trust the score it gives.

The headline feature is **Thinking Modes**, two opt-in effort tiers (`high` and `x-high`) that put a skeptical reviewer inside the analysis. Underneath them, 1.3 rebuilds how RAISE maturity scores are formed, so every score traces to an evidence record you can open and check.

## Put a skeptical reviewer in the loop

High mode adds a second pass to every scan. An auditor with no stake in the original analysis re-reads each finding at the code it cites and tries to knock it down, then applies the same skepticism to your Worker Remit. In a controlled test, we planted four fake findings in already-scanned projects. The auditor caught all four, citing the code that disproved them, and killed none of the roughly 48 real findings around them.

> "In 1.2, the false-positive scrub before release was something we did by hand. In 1.3 we shipped the reviewer, not just the scanner."
>
> — Steve Wilson, lead maintainer of Praxen

The surprise was the remit. The auditor flags rules that don't match how the agent actually works: permissions the policy describes that the agent doesn't have, rules that contradict each other, claims the documentation doesn't back up. Run against our own benchmark remits, it found the same problems our manual review had, caught one we missed, and showed that one of our own bug reports overstated a problem. Each scan sharpens the policy you hold the agent to.

## A single scan can miss things. Now there's a mode for that.

Our [run-to-run variability](https://open-agent-ai-security.github.io/praxen/guide/understanding-variability.html) docs have always been clear that one scan can miss findings, and the advice was to run more than once when the target matters. In our testing on large codebases, a single scan missed roughly 1 in 6 High-severity findings. Not because they were hard to verify, but because no single pass reads a big workspace exhaustively.

X-high mode turns that advice into a feature: three independent scans, automatically merged and adjudicated into one report by the same auditor machinery. The rule is simple. A finding makes the report if the code proves it, not if the scans outvote each other. If one scan of three caught something and the code backs it up, it stays. If all three agreed on something the code doesn't support, it's out.

One example from our validation runs: in a sample agent, the function meant to verify who sent a message accepted any sender whose address simply started with the right text. An authentication bypass, and only one scan in three caught it. Under x-high it made the report.

## Scores you can check

1.3 also fixes a bias in how RAISE maturity scores were formed. The old pipeline scored early in the run, from the model's working memory, and it gave credit for safety features that were merely available rather than actually in use. An opt-in flag that defaults to off could read as a deployed control.

Now scoring happens at the end, from evidence written to disk: per-category notes, a twelve-point maturity sweep that records verified absence as carefully as a hit, and the finding themes. You can open the evidence file beside the report and see what every number rests on.

We didn't just trust the new scores. Everywhere old and new disagreed, we put both answers in front of an independent AI judge, blind, with full access to the source. It sided with the new scores 22 times out of 24. The corrections went both ways, down where credit wasn't earned and up where real practice had been invisible. A scorer that was merely harsher couldn't do that.

One honest limit: there is no ground-truth RAISE score. We can show specific 1.2 numbers were wrong under the categories' own definitions, so "more accurate" is the claim the evidence supports. Because scores moved, 1.3 ships a fresh frozen baseline of all 12 public benchmark targets, and 1.3 scores aren't comparable to 1.2 scores scan-for-scan.

The two features also compound. On our two least consistent benchmark targets, x-high on the new scoring produced identical scores across independent runs. Neither piece does that alone.

## What the modes cost

In our testing on Claude Opus 5, high mode ran about 1.4x the tokens and 1.3 to 1.6x the wall-clock of a standard scan. X-high ran about 4x the tokens but only 2 to 2.5x the wall-clock, since its three scans run concurrently. The standard path is unchanged, and modes are opt-in, selected in plain language when you invoke a scan.

## Also in 1.3

- Sharper detection: user-supplied values flowing into file paths, deployment artifacts (Helm, Terraform, compose) as first-class scan inputs, better-calibrated confidence when a control is verifiably absent
- Cleaner reports: RAISE scores render as five discrete pills, and placeholder secrets like `${VAR}` are no longer redacted as if they were real
- New guides on [hardening a remit](https://open-agent-ai-security.github.io/praxen/guide/writing-remits.html) with a high-mode audit, and on [Thinking Modes](https://open-agent-ai-security.github.io/praxen/guide/thinking-modes.html) themselves

## Get Praxen 1.3

Praxen 1.3 installs from the Open Agent AI Security community marketplace.

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

Then point it at an agent and ask for a Praxen analysis. When the target matters, ask for high mode. Full instructions, including the no-marketplace path for any other coding agent, are in the [installation guide](https://open-agent-ai-security.github.io/praxen/guide/installation.html); the [project home page](https://open-agent-ai-security.github.io/praxen/) has the refreshed 12-agent benchmark, and the source lives on [GitHub](https://github.com/open-agent-ai-security/praxen).

Try the release and let us know what the auditor finds.
