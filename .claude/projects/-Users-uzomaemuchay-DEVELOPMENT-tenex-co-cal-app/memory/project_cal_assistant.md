---
name: Cal Assistant Project Context
description: Calendar AI assistant app - tech stack decisions, architecture, and current status
type: project
---

Cal Assistant is an AI-powered calendar management web app.

**Stack decided:**
- Frontend: React + DaisyUI + TailwindCSS
- Backend: Django + Django Ninja + django-allauth (headless)
- Database: PostgreSQL
- Agent: Agno framework + Claude (reasoning engine)
- Google APIs: google-api-python-client (NOT Agno's built-in Google tools, to avoid OAuth conflicts)
- Optimization: Google OR-Tools (CP-SAT)

**Key architecture decisions:**
- Google-only auth via allauth, single OAuth flow with calendar + gmail scopes
- Calendar events synced to Postgres (not just live API reads) for text-to-SQL analytics
- Agno used as orchestration only; Google API calls use official Python client with Django-managed tokens
- Agent follows GAME loop (Goal-Action-Memory-Environment)
- Multi-calendar data model, but V1 limited to primary calendar
- Dashboard (saved queries from chat) spec'd for V2, not built in V1

**Why:** This is a Tenex project. Full spec in docs/product-spec.md, design brief in docs/design-brief.md.

**How to apply:** Reference the spec docs for all implementation decisions. Stack choices are final unless user revisits.
