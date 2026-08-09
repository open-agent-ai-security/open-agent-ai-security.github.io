---
title: "Ecosystem Spotlight: CogniSafe Scores AI Safety from Observra Telemetry"
author: Open Agent and AI Security Community
date: 2026-08-09
summary: UK-based CogniSafe, an AI trust and safety platform, has adopted Observra as the telemetry layer for its runtime scoring pipeline, plugging straight into the events teams already collect instead of building its own instrumentation.
tags: community, observra, ecosystem
published: yes
image: cognisafe-observra.png
image_alt: "CogniSafe × Observra: Observra telemetry, safety-scored."
---

One of the best things about building open source is watching other people build on it. Today's example: [CogniSafe](https://cognisafe.uk/), a UK-based AI trust, safety and assurance platform, has published an official [Observra integration](https://docs.cognisafe.uk/integrations/telemetry-ingest) — and specifically chose Observra as the way to get telemetry out of running agents.

## The interesting part: why Observra

CogniSafe runs a runtime proxy that watches the whole agentic execution path (model calls, tool calls, inter-agent messages) and scores it for risk. To do that, it needs a real-time feed of what an agent is actually doing. Rather than build and maintain their own instrumentation across every framework a customer might run, they built on top of the telemetry teams are already capturing with Observra.

## How the integration works

CogniSafe's [telemetry-ingest integration](https://docs.cognisafe.uk/integrations/telemetry-ingest) routes the Observra telemetry a team already collects straight into CogniSafe's pipeline. The setup is one line: point Observra's webhook backend at their ingest endpoint.

```python
observra.initialize(
    backend="webhook",
    webhook_url="https://api.cognisafe.uk/ingest/observra",
)
```

From there, Observra does what it always does: capturing model calls, tool activity, costs, and errors across Google ADK, Claude Agent SDK, OpenAI, LangChain, and Pydantic AI. No SDK changes to the agent, no second instrumentation layer, no framework-by-framework integration work on CogniSafe's end.

A detail we particularly like: their docs call out pairing the integration with Observra's built-in PII redaction, so CogniSafe scores sanitized events rather than raw user data. That's exactly the layered design we hoped people would build, with privacy handled at the edge by the SDK and analysis downstream on clean data.

## Why this matters

Observra's whole premise is that agent telemetry should be an open, common format that any tool can consume, rather than a walled garden. When a commercial platform's fastest path to "watch what an agent does" is to ingest that format directly instead of writing their own collector, that's the format doing its job. If you're building on Observra's event stream too, [we'd love to hear about it](https://www.linkedin.com/company/open-agent-and-ai-security-community/).

**Explore:** [CogniSafe](https://cognisafe.uk/) · [their Observra integration docs](https://docs.cognisafe.uk/integrations/telemetry-ingest) · [Observra on GitHub](https://github.com/open-agent-ai-security/observra)
