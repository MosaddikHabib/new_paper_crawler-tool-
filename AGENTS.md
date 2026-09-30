# Agent Workflows & Instructions

This repository is configured with **OpenSpec** (Spec-Driven Development) and **gstack** (Garry Tan's specialist development suite).

## 🚀 OpenSpec Workflows
- `/opsx-propose "feature idea"`: Propose a new specification change.
- `/opsx-apply "change-id"`: Implement tasks defined in the specification change.
- `/opsx-archive "change-id"`: Archive and merge completed changes into main specs.
- `openspec list`: List active changes and specifications.
- `openspec validate <change-id>`: Validate specification and task checklist status.

## 🛠️ gstack Workflows
Use gstack specialist tools when executing software lifecycle phases:
- `/office-hours`: Product interrogation, premise challenges, and structured design doc creation.
- `/autoplan`: Sequential CEO → Design → DX → Engineering review pipeline.
- `/plan-ceo-review`: CEO-level product challenge and 10x value scope evaluation.
- `/plan-eng-review`: Engineering architecture & tech stack locking.
- `/plan-design-review` & `/design-review`: Catch UI slop, enforce modern typography and design system tokens.
- `/review`: Rigorous production code review before shipping.
- `/qa` & `/qa-only`: Automated browser QA testing.
- `/cso`: Security audit (OWASP Top 10, STRIDE threat modeling).
- `/ship`: Release readiness, PR creation, and deployment validation.
- `/browse`: Headless and interactive web browsing engine.

## gstack Ethos & Reuse Ladder
- **Boil the Ocean**: Do the complete thing—tests, edge cases, error paths. Shortcuts require an explicit decision.
- **Search Before Building**: Check existing repo utilities, standard library, native platform features, and installed dependencies before adding new code.
- **User Sovereignty**: Models recommend, the user decides. Ask before changing the user's stated direction.
- **Build for Yourself**: Solve the real, specific problem over hypothetical generality.
