---
title: "Community Spotlight: Mapping OWASP Risks with Praxen"
author: Open Agent and AI Security Community
date: 2026-07-14
summary: Community member Steve Wilson used Praxen to test 12 open-source agent projects against both the OWASP LLM and Agentic Top 10 — and found the two risk taxonomies overlap more than most people expect.
tags: community, praxen, owasp
published: yes
image: steve-owasp-agentic-findings.png
image_alt: "When OWASP LLM Risks Meet Agentic Risks — Steve Wilson reading the OWASP Top 10 for LLM Applications and OWASP Top 10 for Agentic Applications, next to a reclining robot."
---

Our community member Steve Wilson just published his latest findings, using Praxen to analyze 12 open-source agent projects against both the OWASP Top 10 for LLM Applications and the OWASP Agentic AI risk framework.

Across 114 findings, nearly half — 46 — spanned both frameworks, with the strongest overlap between Excessive Agency (the most common LLM-side finding) and Unexpected Code Execution (the most common agentic-side finding). His takeaway: the two taxonomies describe different layers of the same failures — the LLM framework catches model-level weaknesses, the agentic framework catches what happens when those weaknesses turn into real operational consequences — and real-world security failures often chain across both.

Check it out: [When OWASP LLM Risks Meet Agentic Risks](https://www.linkedin.com/pulse/when-owasp-llm-risks-meet-agentic-steve-wilson-wkeec/)
