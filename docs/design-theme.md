# Design System Specification: Chronicle Modern

## 1. Creative North Star: "The Digital Curator"
Chronicle Modern is a design system that bridges the gap between **analog warmth** and **SaaS modernity**. It rejects the sterile, cold aesthetics of typical productivity tools in favor of an interface that feels like a high-quality physical planner—grounded, quietly opinionated, and information-dense—while incorporating modern UI patterns for ease of use.

---

## 2. Visual Principles
*   **Tactile Layers:** Surfaces feel like high-quality paper or cards sitting on a desk. We use subtle shadows and 8px–12px corner rounding to provide a friendly, contemporary feel without losing the "analog" soul.
*   **Editorial Density:** Layouts prioritize content and information hierarchy over "empty" whitespace. Like a well-designed broadsheet or journal, every element has a clear purpose and position.
*   **Restrained AI Identity:** The AI is a "silent partner." No mascots, floating orbs, or sci-fi glows. It is distinguished by subtle background tints and precise labels, behaving like a professional colleague.

---

## 3. Color Palette
*   **Canvas (Base):** `#FAF8F5` (Warm Cream). A soft, off-white foundation that reduces eye strain and provides a paper-like feel.
*   **Ink (Text):** `#1B1C1A` (Near-Black). A warm, deep charcoal used for maximum readability.
*   **The Signature Accent:** `Terracotta / Burnt Sienna` (`#C05746`). This single earthy tone is the only "active" color in the system. It is used for primary buttons, current day indicators, and critical call-to-actions.
*   **The Archive (Secondary):** Muted, desaturated stones and warm grays (`#F5F3F0`, `#E6E4E1`) for containers, sidebars, and inactive states.

---

## 4. Typography
*   **Headlines & Signature Elements:** **Newsreader (Serif)**. Used for the product logo, main headers, and "editorial" moments. It provides the system's character and archival weight.
*   **Interface & Functional Text:** **Plus Jakarta Sans (Humanist Sans-Serif)**. A modern, highly legible typeface used for all UI labels, navigation, and body copy.
*   **Data & Chronometrics:** **Space Grotesk** or **IBM Plex Mono**. Used for times, dates, and analytical charts to convey technical precision and trustworthiness.

---

## 5. Component Guidelines
*   **Primary Action Buttons:** Solid terracotta fill, white text, 8px corner radius. They should "pop" against the cream background.
*   **Secondary/Outline Buttons:** 1px border in 'Ink' or 'Terracotta', no fill, 8px radius.
*   **Button size scale (production-compact):**
    *   **`sm` (default app controls):** `36px` height, `12px` horizontal padding, `14px` text.
    *   **`md` (primary page actions):** `40px` height, `14px` horizontal padding, `14px` text.
    *   **`lg` (auth CTA only when needed):** `44px` height, `16px` horizontal padding, `14px` text.
    *   Avoid 48px+ button heights on normal application screens unless accessibility or touch-surface requirements explicitly demand it.
*   **Cards & Containers:** Background color `#FFFFFF` or `#FBF9F6`, 1px subtle border or a very soft, diffused shadow.
*   **Calendar Grid:** Thin, ruled lines (`#1B1C1A` at 10% opacity). The grid should recede into the background, letting events be the hero.
*   **Chat Bubbles:** AI messages have a subtle warm tint (`#F2EDE4`) to distinguish them from user messages, which are styled as plain text or light cards.

---

## 6. Iconography
*   **Style:** Line-based, thin stroke (2px).
*   **Weight:** Light or Regular to match the refinement of the typography.
*   **Library:** Phosphor Icons or Lucide.

---

## 7. Interactive Philosophy
*   **Subtle Transitions:** Hover states use slight color shifts or very gentle scaling. Avoid aggressive animations.
*   **Direct Manipulation:** The calendar and chat are deeply integrated; actions in the chat (like "Create Event") should reflect instantly on the calendar grid with a subtle highlight.

## 8. Size and Density (Type Scale)

*   **Default UI & body:** Use a strict **production baseline** of **14px** for body and control text.
*   **Secondary labels/captions/metadata:** Use **12px** as the default secondary scale.
*   **Line height:** Tighter than marketing landing pages—**1.4–1.5** for paragraphs, **1.2–1.35** for single-line UI labels—so screens feel efficient and scannable, not airy.
*   **Density over billboard:** Chronicle Modern is information-forward; type should **recede** enough that events, times, and copy remain the focus. When in doubt, **one step smaller** on secondary text rather than enlarging primary text.
*   **Heading scale:** Keep headings restrained. Typical app page title range should be around **22–30px desktop** and **20–24px mobile**. Section titles should usually remain **16–20px**.
*   **Authentication surfaces:** Login and auth-entry screens should feel polished but still unmistakably like a production app. Keep the **brand wordmark restrained** at roughly **20–24px** on desktop and **18–22px** on mobile. Primary auth headings like “Welcome back” should sit around **22–28px** on desktop and **20–24px** on mobile.
*   **Auth supporting copy:** Keep sign-in explainer text around **14px** with concise, operational wording. Footer/legal/support links should sit at **12px** so they support the flow without competing with the main action.
*   **Production copy over concept copy:** Authentication pages should read like a real working product, not a speculative landing page. Prefer direct language such as “Sign in to access your calendar workspace” over abstract positioning or visionary product statements.

## 9. Universal Theme Tokens and Enforcement

*   **Single source of truth:** All sizing, spacing, radius, and component dimensions must come from shared theme tokens (global CSS variables or design-system primitives), not one-off values inside feature files.
*   **No per-page component sizing:** Feature-level files should consume semantic classes/tokens (`button-sm`, `button-md`, body/caption tokens, etc.) instead of redefining button heights, font sizes, or paddings locally.
*   **Token-first updates:** If a component needs a new size variant, add it to the universal theme first, then apply it across screens. Do not introduce ad hoc sizes in page-specific CSS.
*   **Consistency check:** PR review should reject local style overrides that duplicate or conflict with global tokenized sizes.
