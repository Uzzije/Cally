# Cal Assistant - Design Brief

**For:** AI UI Designer / Visual Designer
**Project:** Calendar Assistant Web App
**Date:** April 4, 2026

---

## Project Context

You are designing a calendar + chat AI assistant web app. The user authenticates with Google, sees their calendar, and chats with an AI agent that can read/modify their schedule and draft emails. The chat renders rich content inline (charts, action cards, email previews).

See `product-spec.md` for full feature details and screen layouts.

---

## ANTI-BRIEF -- What This Must NOT Look Like

Do NOT use:
- Purple, indigo, or blue-violet gradients
- Glassmorphism, frosted glass, or translucent cards
- Floating orbs, particles, aurora blurs, or mesh gradients
- Neon accents, glowing borders, or sci-fi aesthetics
- The "default AI startup" look (dark bg + bright accent)
- Overly rounded, bubbly UI that feels like a toy
- Sparkle/magic/wand iconography for AI actions
- A chat interface that visually mimics ChatGPT or Gemini

This is a productivity tool, not a tech demo. It should feel like opening a high-quality planner, not entering a spaceship.

---

## Design Direction: "Analog Warmth, Digital Precision"

Think: Moleskine planner meets Bloomberg terminal meets Muji. Confident, warm, information-dense, quietly opinionated.

---

## Color Palette

- **Base**: Warm off-white / cream (#FAF8F5 range) -- not sterile white
- **Primary surface**: Warm light gray with a hint of warmth
- **Text**: Near-black with warmth (#2C2A27 range), not pure #000
- **Accent**: ONE bold, non-tech color. Consider:
  - Terracotta / burnt sienna (warmth, earthiness)
  - Deep olive / sage (calm, grounded)
  - Mustard / ochre (energy without loudness)

  Pick ONE. Use it sparingly -- buttons, active states, the current day indicator. Everything else is neutral.
- **Calendar events**: Muted, desaturated tones -- no candy colors. Think ink on paper, not highlighters.
- **Chat agent messages**: Subtle warm tint background, not a bright colored bubble.

---

## Typography

- **Headers**: A serif or slab-serif with personality. Consider: Instrument Serif, Fraunces, Newsreader, or DM Serif. This is the signature element -- it says "this is not another SaaS app."
- **Body/UI**: A clean humanist sans-serif. Consider: DM Sans, Inter, or Satoshi. Readable at small sizes, not robotic.
- **Monospace** for data/numbers in charts: JetBrains Mono or IBM Plex Mono -- gives analytics a precise, trustworthy feel.
- **Avoid**: Geometric sans-serifs that feel cold (Poppins, Montserrat). Avoid anything that screams "Figma template."

---

## Layout Principles

- Information-dense but not cluttered. Show more, chrome less.
- Calendar grid should feel like a printed weekly planner -- thin ruled lines, not heavy bordered boxes.
- Cards and containers: Subtle borders or light shadows, NOT floating glassmorphic panels. Think printed paper sitting on a desk, not hovering in space.
- The chat panel should feel like a notebook margin -- present but not dominant. It's a tool, not the spectacle.
- Use whitespace intentionally for hierarchy, not as filler.

---

## Component Style

- **Buttons**: Solid fill for primary (accent color), outlined for secondary. Slightly squared corners (4px, not 12px). No pill shapes.
- **Input fields**: Simple underline or thin border. Not chunky rounded boxes.
- **Icons**: Line-style, thin stroke. Consider Phosphor Icons (light weight) or Lucide. No filled/chunky emoji-style icons.
- **Charts** (inline in chat): Minimal, editorial style. Think NYT data visualization -- thin lines, muted fills, clear labels. Not dashboard-widget style with heavy drop shadows and gradient fills.
- **Action cards** (calendar creates, email drafts): Left-bordered cards with accent color stripe. Clean, structured, scannable. Like a to-do item in a paper planner.
- **Email previews**: Styled like an actual email -- mimicking a mail client's compose window, not a generic card.

---

## AI Presence

- The AI is not a character. No avatar, no robot face, no animated typing indicator with bouncing dots.
- Agent messages are distinguished by background tint and a small label ("Assistant"), not by a chatbot avatar.
- When the agent is working (calling tools, fetching data), show a quiet progress state -- a thin animated line or subtle text like "Checking your calendar..." Not a pulsing orb or spinner.
- The AI should feel like a capable colleague writing you notes, not a chatbot performing for you.

---

## Calendar Specific

- **Current day**: Accent color dot or underline on the date number. Not a giant highlighted circle.
- **Events**: Compact, left-color-coded by category (muted tones). Show title + time, truncate gracefully.
- **Blocked time** (workouts, focus): Diagonal hatching or a subtle pattern fill -- distinguishable from events without using a loud color.
- **Hour grid**: Light, thin lines. Time labels in small monospace. The grid recedes; events pop.

---

## Dark Mode (Secondary)

- NOT black (#000) backgrounds. Use very dark warm gray (#1C1B19 range).
- Accent color shifts slightly lighter/warmer.
- Calendar grid lines become very subtle warm gray.
- The feel should be "reading by lamplight" not "spaceship cockpit."
- Light mode is the default.

---

## Mood References

For visual direction, not copying:

- Notion's restraint with a warmer palette
- Things 3's quiet confidence
- Linear's density without its coldness
- A Monocle magazine layout
- Dieter Rams: "Less, but better"

---

## Screens to Design

1. **Login** -- minimal, warm, single Google sign-in button
2. **Onboarding** -- preference setup (2-3 steps)
3. **Main view** -- calendar (weekly, 60%) + chat panel (40%)
4. **Chat states:**
   a. Text response with inline bar chart
   b. Action confirmation (3 calendar events proposed)
   c. Email draft preview with send/edit/discard
   d. Clarification question from agent
   e. Agent working/loading state
5. **Settings page**
6. **Dashboard** (saved query cards) -- layout only, V2
7. **Mobile responsive**: calendar tab, chat as full-screen tab

---

## Deliverables

- High-fidelity mockups in light mode for all screens listed above
- One key screen (main view) in dark mode to establish the dark palette
- Component library sheet showing: buttons, inputs, cards, chart styles, action cards, email draft card, typography scale
- Color palette with hex values and usage guidelines
