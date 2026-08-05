---
title: "Promptfall: Ten Vulnerabilities. One Hero. Zero Slide Decks."
author: Steve Wilson
date: 2026-08-05
summary: Our newest open-source project is a browser platformer that teaches the 2026 OWASP Top 10 for LLM Applications, one stomped vulnerability at a time. No install, no account, no homework. Just play.
tags: release, promptfall, owasp
published: yes
image: promptfall-launch.jpg
image_alt: "Promptfall — learn the OWASP Top 10 for LLMs. Ten vulnerabilities. One hero."
---

We've shipped a telemetry SDK. We've shipped a security scanner. Today we're shipping... a video game?

Yes. Meet **[Promptfall](https://open-agent-ai-security.github.io/promptfall/)**, a modern browser platformer that turns the [2026 OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/) into a playable campaign. It runs right in your browser, on desktop or phone. There's no install, no account, and no backend. Click the link and you're playing.

## The premise

Prompt Injection, Data Poisoning, Excessive Agency... the OWASP Top 10 for LLMs is essential reading for anyone building with AI. It is also, let's be honest, a document most people skim once and file away.

So we gave each risk a body, a bad attitude, and a boss level.

You play as **Praxi** (yes, the Praxen fox, moonlighting from their day job of scanning agents) running a gauntlet of eleven high-tech environments. Each of the first ten levels is one OWASP risk, brought to life as an animated threat you have to stomp. Defeat every threat in a level to drop the force field and reach the exit.

## Sneaky, sneaky education

Here's the trick: every level hides six educational encounters in the action. A definition, why the risk matters, two real-world examples, and two defenses, all caught mid-jump without ever stopping the game. Each level ends with a quick quiz to lock it in, drawn from a bank of **33 questions**. By the time you've cleared LLM05, you actually know what Data and Model Poisoning is, how it happens, and what to do about it. You just also happened to be dodging things while learning it.

![Level 1 in action: Praxi catches a "Why It Matters" lesson on Prompt Injection mid-level, with "Borrowed Hands" playing in the HUD and two threats waiting up ahead.](promptfall-gameplay-llm01.jpg)

Beat all ten levels and you unlock **The Gauntlet**: every threat returns for one final wrap-up run, each carrying a single key insight worth remembering. All told, that's **70 in-game learning opportunities** across the campaign. (We counted. It's in the source code. You can check.) Survive the Gauntlet and you've effectively speed-read the whole Top 10, with better retention than any compliance training we've ever sat through.

## The soundtrack slaps, and it's studying

Promptfall ships with **12 original songs**, one per level plus a title theme and a Gauntlet reprise, and they're not background filler: the lyrics reinforce what each level teaches. Prompt Injection gets "Borrowed Hands." Excessive Agency gets "Too Much Rope." Misinformation gets "Beautifully Wrong," and Improper Output Handling closes on "Passed Without Question." If you catch yourself humming a mitigation strategy three days later, that's the design working.

## The details

- **The whole game is open source** (Apache 2.0), like everything we build. Not just "the engine": the campaign data, the lesson content, the quiz bank, the art, and the music all live in the [GitHub repo](https://github.com/open-agent-ai-security/promptfall). Peek at how it works, borrow it for a security-training session, or contribute a level idea.
- **Runs anywhere.** The whole game is static files served from GitHub Pages. Desktop gets keyboard controls, mobile gets touch controls, and pausing freezes everything so you can actually read the hints.
- **Privacy-respecting.** Cookieless pageview counters only. We don't record your controls, your progress, or how many times LLM06 got you. (It got us plenty.)

## Why a game?

Because security education mostly fails at the "anyone voluntarily does it" step. The OWASP Top 10 for LLMs matters to developers, security teams, students, and honestly anyone deploying AI, and we wanted a way in that doesn't feel like homework. If one person ships a safer agent because a pixel-art vulnerability once chased them across a platform, that's a win.

**Play it now: [open-agent-ai-security.github.io/promptfall](https://open-agent-ai-security.github.io/promptfall/)**

Tell us your Gauntlet time. We won't tell you ours.
