---
title: "Ecosystem Spotlight: CogniSafe Scores AI Safety from Observra Telemetry"
author: Open Agent and AI Security Community
date: 2026-08-09
summary: UK-based CogniSafe now ingests Observra telemetry directly into its AI trust and safety platform, scoring agent behavior against the OWASP LLM Top 10 from the events teams already collect.
tags: community, observra, ecosystem
published: yes
image: cognisafe-observra.png
image_alt: "CogniSafe × Observra: Observra telemetry, safety-scored. CogniSafe scores agent behaviour against the OWASP LLM Top 10 from the telemetry you already collect."
---

One of the best things about building open source is watching other people build on it. Today's example: [CogniSafe](https://cognisafe.uk/), a UK-based AI trust, safety and assurance platform, has published an official [Observra integration](https://docs.cognisafe.uk/integrations/telemetry-ingest).

## What CogniSafe does

CogniSafe covers the AI security lifecycle from both ends. Before launch, their Recon tool runs an automated battery of adversarial probes (prompt injection, jailbreaks, system-prompt extraction, data leakage, excessive agency) against your prompts and endpoints, and hands back an OWASP-mapped posture score with remediation guidance. After launch, their runtime proxy watches the whole agentic execution path: model calls, MCP tool calls, and inter-agent messages, scoring all ten OWASP LLM Top 10 threats asynchronously with per-agent attribution, block mode, and tamper-evident audit trails.

Their pitch, which will sound familiar to this community: endpoint filtering stops at the model, but the risk doesn't. Agents act, call tools, and message each other, and that's where the interesting failures live.

## Where Observra comes in

CogniSafe's [telemetry-ingest integration](https://docs.cognisafe.uk/integrations/telemetry-ingest) lets teams route the Observra telemetry they already collect straight into CogniSafe's scoring pipeline. The setup is one line: point Observra's webhook backend at their ingest endpoint.

```python
observra.initialize(
    backend="webhook",
    webhook_url="https://api.cognisafe.uk/ingest/observra",
)
```

From there, Observra does what it always does, capturing model calls, tool activity, costs, and errors across Google ADK, Claude Agent SDK, OpenAI, LangChain, and Pydantic AI, and CogniSafe turns that stream into OWASP-aligned safety scores, governance dashboards, alerts, and audit evidence. No SDK changes to the agent, no second instrumentation layer.

A detail we particularly like: their docs call out pairing the integration with Observra's built-in PII redaction, so CogniSafe scores sanitized events rather than raw user data. That's exactly the layered design we hoped people would build, with privacy handled at the edge by the SDK and analysis downstream on clean data.

## Why this matters

Observra's whole premise is that agent telemetry should be an open, common format that any tool can consume, rather than a walled garden. A commercial safety platform choosing to ingest that format natively is the ecosystem working as intended. If you're building on Observra's event stream too, [we'd love to hear about it](https://www.linkedin.com/company/open-agent-and-ai-security-community/).

**Explore:** [CogniSafe](https://cognisafe.uk/) · [their Observra integration docs](https://docs.cognisafe.uk/integrations/telemetry-ingest) · [Observra on GitHub](https://github.com/open-agent-ai-security/observra)
