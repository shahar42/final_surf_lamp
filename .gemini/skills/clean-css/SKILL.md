---
name: clean-css
description: Guidance on writing clean, efficient, and architectural CSS. Use when refactoring stylesheets, implementing design systems, or seeking advice on modern CSS best practices (e.g., utility-first, BEM, CSS variables).
---

# Clean CSS

## Principles

1.  **Utility-First / Functional CSS:** Prefer small, single-purpose classes (like Tailwind) over large, semantic classes. This reduces CSS bundle size and prevents "append-only" stylesheets.
2.  **Predictability:** Styles should behave consistently regardless of context. Avoid deep nesting and specificity wars.
3.  **Composition over Inheritance:** Build complex components by composing simple utilities.
4.  **Design Tokens:** Use CSS variables for all design values (colors, spacing, typography) to ensure consistency and themeability.
5.  **Mobile-First:** Write base styles for mobile, then use media queries (min-width) for larger screens.

## Workflow

### 1. Refactoring Legacy CSS
- **Audit:** Identify repeated patterns and hardcoded values.
- **Tokenize:** Extract colors, spacing, and fonts into CSS variables (root level).
- **Flatten:** Replace nested selectors with direct classes or utility classes.
- **Purge:** Remove unused styles.

### 2. Creating New Components
- Start with HTML and apply utility classes.
- Only extract to a component class (`.btn`, `.card`) if the pattern is repeated frequently *and* complex enough to justify the abstraction.
- Keep component classes "open" to modification (avoid `!important`).

## Architectural Patterns

### The "Single Source of Truth"
Define your design system in one place (usually `:root` variables or a config file).
Refer to [DESIGN_TOKENS.md](references/design_tokens.md) for standard token naming conventions.

### Managing Layouts
Use Flexbox for 1D layouts and Grid for 2D layouts. Avoid floats and absolute positioning for structural layout.

### State Management
Use `data-` attributes for state (e.g., `data-state="active"`) instead of adding/removing classes, to separate concerns between styling and logic.

## Resources
- **Reference**: [MODERN_CSS_GUIDE.md](references/modern_css_guide.md) - Deep dive into Flexbox, Grid, and logical properties.