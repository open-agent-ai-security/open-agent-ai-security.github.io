---
title: Observra 1.1: Bring Observability to Any AI Agent
author: Steve Wilson
date: 2026-08-06
summary: Observra 1.1 opens its telemetry pipeline to any custom agent framework — no adapter required — plus local storage, a live terminal dashboard, and support for 100+ LLM providers.
tags: release, observra
published: no
image: observra-1.1-release.png
image_alt: Observra 1.1 release — Bring observability to any AI agent.
---

Today we're releasing **Observra 1.1**, a major step toward making structured, security-aware telemetry available to every AI agent—regardless of the framework, model provider, or infrastructure behind it.

The headline feature is simple: **Observra now works with custom and in-house agent frameworks without requiring a dedicated adapter.**

That means teams no longer need to wait for us to add native support for their framework before they can capture consistent telemetry across prompts, model calls, tool activity, costs, errors, and agent sessions.

## One telemetry pipeline for any framework

Observra already includes native integrations for several popular agent frameworks. In 1.1, we're opening the same telemetry pipeline to virtually any agent implementation.

Developers can now instrument custom agent stacks while retaining Observra's built-in capabilities, including:

- Automatic redaction of sensitive information
- Prompt-injection detection
- Token and cost tracking
- Structured model and tool-call events
- A normalized telemetry schema across frameworks

We have also improved session tracking for existing framework integrations. Multi-step agent runs now maintain more reliable event histories and more accurate cost attribution across the full session.

Teams are already putting this to work, instrumenting agents such as OpenClaw and Hermes with no adapter needed, just `emit()` or a webhook call.

> "Agent frameworks are evolving too quickly for observability to depend on a growing collection of one-off integrations," said **Neville Mascarenhas, lead maintainer of Observra**. "With Observra 1.1, developers can instrument the agent they actually built, using the framework—or no framework—they chose, and still get the same consistent telemetry and security controls."

## Store everything locally

Observra 1.1 introduces a new local storage option for teams that want a complete, queryable record of agent activity without deploying a separate backend.

This makes it easier to:

- Inspect historical agent sessions
- Investigate unexpected behavior
- Compare model and tool activity over time
- Analyze token usage and cost
- Develop and test agents entirely on a local machine

It is especially useful during development, experimentation, and early-stage deployments where standing up additional infrastructure would add unnecessary friction.

## Watch your agent work in real time

The release also includes a new terminal dashboard that provides a live view of agent activity as it happens.

From the terminal, developers can follow:

- Active sessions
- Model requests and responses
- Tool calls
- Token consumption
- Estimated spend
- Errors and security events

Instead of reviewing logs after something goes wrong, teams can now see how an agent is behaving while it is running.

## Broader model-provider support

Observra 1.1 also expands model coverage through support for more than 100 LLM providers.

Whether an agent uses a major commercial model, an open model, or a less common provider, developers can capture the same core observability signals without rebuilding their instrumentation for each platform.

## Built in the open

Observra is an open-source project developed under the **Apache 2.0 license** as part of the Open Agent AI Security community.

It is developed alongside **Praxen**, our open-source agent behavior verification project. While Praxen helps determine whether an agent behaves within its intended boundaries, Observra provides the underlying visibility into what the agent did, which tools it used, what it consumed, and what happened along the way.

Together, the projects are intended to help developers and security teams better understand, test, and secure increasingly autonomous systems.

## Get Observra 1.1

Observra 1.1 is available now through `pip`.

```bash
pip install --upgrade observra
```

We'd love for the community to try the new release, instrument your agents, report issues, and tell us what you want to see next.
