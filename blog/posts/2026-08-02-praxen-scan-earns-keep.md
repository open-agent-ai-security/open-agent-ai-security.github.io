---
title: When a Security Scan Earns Its Keep
author: Open Agent and AI Security Community
date: 2026-08-02
summary: A developer building a security-sensitive AI agent put Praxen to work on their own codebase. Here's what it found, and how fast it got fixed.
tags: praxen, security
published: yes
image: praxen-scan-earns-keep.png
image_alt: When a security scan earns its keep — Praxen, real findings on a real security-sensitive agent, verified and fixed the same day.
---

We built Praxen to help developers verify what their agents actually do, versus what they intend, so nothing tells us we're on the right track like hearing from people building real, security-sensitive systems. We're always glad to hear from our users, and we especially love it when the feedback is great.

Recently, a developer building an AI agent with serious security requirements put Praxen to work on their own codebase. They asked to stay anonymous, and we're happy to respect that, so what follows is shared with every identifying and proprietary detail stripped out. The findings themselves are what matter.

Praxen surfaced a handful of real issues, and the developer verified and fixed them the same day:

- **A data-exposure gap in a diagnostics export.** A redaction routine scrubbed one field, but the same sensitive value rode along, intact, in a sibling field of the same export. The kind of leak that's easy to miss and ends up in every export from then on. It's now fixed so every value-bearing field scrubs, with a test that asserts the secret appears nowhere in the output.
- **A tool description quietly teaching an unsafe ordering of operations**, in the instructions the model reads. Corrected to spell out the safe pattern instead.
- **Untrusted third-party text flowing unescaped into a privileged instruction channel.** A classic prompt-injection surface, now defanged.

In the developer's own words, the report was "very impressive": the high-priority findings were genuinely high-priority, and, a detail we were glad to hear, it was token-efficient. The severity ranking did its job. The things that mattered rose to the top.

This is exactly what Praxen is for: a pre-ship security gate that checks an agent's actual behavior against its declared intent, before it reaches users. Feedback like this, real findings on a real system, from a developer who holds a high bar, is exactly how we sharpen it.

If you're building a security-sensitive agent, we'd love to hear from you. Try Praxen, and tell us what worked and what didn't. Anonymous or not, your feedback shapes where we take it next.

**Grab Praxen today and scan your own agents:** [github.com/open-agent-ai-security/praxen](https://github.com/open-agent-ai-security/praxen)
