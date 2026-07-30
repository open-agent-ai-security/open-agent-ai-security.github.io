---
title: Praxen 1.2: Now Aligned to the 2026 OWASP Top 10 for LLM Applications
author: Steve Wilson
date: 2026-07-29
summary: Praxen 1.2 aligns risk findings to the 2026 OWASP Top 10 for LLM Applications, with clearer scoring, scan-to-scan comparisons, and a new shareable Worker Remit.
tags: release, praxen
published: yes
image: praxen-1.2-release.png
image_alt: Praxen 1.2 release — 2026 OWASP Top 10 for LLM.
---

Today we're releasing **Praxen 1.2**, with support for the 2026 OWASP Top 10 for LLM Applications.

This is more than a terminology update. Praxen now evaluates agent risks using the latest OWASP guidance, helping teams connect what an agent can do, what it is allowed to do, and where its controls may fall short against the industry's most current risk model.

For developers and security teams, that means Praxen findings are easier to interpret, prioritize, and communicate using a framework the broader industry already recognizes.

> "The 2026 OWASP Top 10 reflects how quickly AI application risk is evolving. Praxen 1.2 brings that guidance directly into the review process, so teams can evaluate real agent capabilities, permissions, and behavior against the latest industry standard."
>
> — Steve Wilson, creator of Praxen and project co-lead for the OWASP Top 10 for LLM Applications

## What's new in Praxen 1.2

Alongside the updated OWASP support, this release includes several improvements designed to make reviews clearer and more useful:

- Updated risk mapping aligned to the 2026 OWASP Top 10 for LLM Applications
- Clearer, more consistent findings through an improved analysis and scoring process
- Scan-to-scan comparisons showing what is new, resolved, or unchanged
- A new human-readable, shareable Worker Remit for developers, security reviewers, auditors, and leadership

Praxen's public 12-agent benchmark remains available for anyone who wants to inspect its performance on real software.

The benchmark was designed to be transparent and repeatable. Each target was analyzed three times against identical inputs, with the median result published. An independent source review examined roughly 130 findings and found that every reviewed issue traced back to real code or configuration.

![OWASP LLM Top 10 coverage by category, showing how findings across the 12-agent benchmark map to each 2026 OWASP category](praxen-1-2-owasp-coverage.png)

## Why the OWASP update matters

Praxen is built to verify whether an agent's actual capabilities and behavior match the role it was authorized to perform.

With 1.2, those reviews are now grounded in the latest OWASP risk categories. Teams can move from a raw technical finding to a recognized security concern without manually translating between the two.

That makes Praxen more useful not only for developers, but also for security teams, risk leaders, and auditors who need a common language for discussing agent security.

## Built in the open

Praxen is available under the Apache 2.0 license as part of the Open Agent AI Security community.

## Get Praxen 1.2

Praxen 1.2 is available now for Claude Code and OpenAI Codex — get it on [GitHub](https://github.com/open-agent-ai-security/praxen).

Try the release, run it against your agents, and let us know what you find.
