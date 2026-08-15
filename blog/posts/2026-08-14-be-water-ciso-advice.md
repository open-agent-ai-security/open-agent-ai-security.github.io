---
title: "Community Spotlight: Be Water, AI Security Advice for CISOs"
author: Open Agent and AI Security Community
date: 2026-08-14
summary: SecureW2's Signal blog sits down with Steve Wilson on the two failure modes CISOs hit with agentic AI, freeze or charge in, and the fundamentals that beat both. The scanner and the monitoring questions he describes are exactly what Praxen and Observra exist to answer.
tags: community, praxen, observra
image: be-water-ciso-advice.png
image_alt: "Praxen + Observra — Community Spotlight: Be water. Steve Wilson on the two failure modes CISOs hit with agentic AI, and the fundamentals that beat both. Q&A at SecureW2 Signal."
---

SecureW2's Signal blog just published a Q&A with Steve Wilson, co-founder of the OWASP GenAI Security Project, Chief AI and Product Officer at Exabeam, and Praxen's lead maintainer. The frame comes from the sparring mat: beginners freeze, wild men charge in, and both get knocked down. Steve sees the same two failure modes in security teams facing agentic AI. Some freeze, staring at hypothetical superintelligent attackers while their own network sits uncataloged and unmonitored. Others charge in with blanket bans on coding agents, which is pointless, because as he puts it, developer adoption is already 100%: "I don't even say it rounds off anymore." The answer is Bruce Lee's: be water. Stay calm, stay flexible, run your game plan.

The game plan he lays out is the one this community is building in the open. Vet an agent the way you'd vet any other software joining your network: know its provenance, scan it for vulnerabilities. "I give you a free scanner, 15 minutes later you'll have an idea what that agent does and doesn't do." That scanner is [Praxen](https://open-agent-ai-security.github.io/praxen/), and the "run it and get scored one to five" he describes is the RAISE score, the capstone process from his book made executable: limit the agent's domain, give it zero-trust identity, manage its supply chain, red-team it, and monitor it continuously. His honest read on the state of the field applies to our own scans too: "Even the most robust agents out there fall down."

And the questions he says every CISO should be asking, "Am I monitoring my agents? Am I baselining them? Am I taking action when they go off the rails?", are the observability half of the story. Verification can't stop at ship time. That's [Observra](https://open-agent-ai-security.github.io/observra/)'s side of the house: recording what agents actually do in production so the baseline is real behavior, not a config file's promise.

Read the full Q&A: ["Be Water": AI Security Advice for CISOs From the OWASP GenAI Security Project Co-Founder](https://securew2.com/signal/be-water-ai-security-advice-for-cisos)
