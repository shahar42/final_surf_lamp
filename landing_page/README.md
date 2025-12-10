# Surf Lamp Landing Page

## Overview
This is the minimalist marketing landing page for the Surf Lamp project. It is designed around Simon Sinek's "Golden Circle" philosophy (Start with Why), aiming to connect emotionally with the user before introducing the technical product.

**Live URL:** [https://surf-lamp-landing.onrender.com](https://surf-lamp-landing.onrender.com)

## Design Philosophy

The page follows a strict narrative flow:

1.  **The Why (Hero Section):**
    *   *Headline:* "We believe the ocean shouldn't stay behind a screen."
    *   *Subtitle:* "Anywhere you go, always take the ocean with you."
    *   *Goal:* Establish shared beliefs and emotional connection.

2.  **The How (Philosophy):**
    *   *Content:* Describes the ambient, intuitive nature of the device. Distilling chaos into elegance.
    *   *Goal:* Explain the unique approach to solving the problem (no apps, no charts).

3.  **The What (Product):**
    *   *Visual:* Single, high-quality showcase of the **Natural Wood** Surf Lamp.
    *   *Specs:* Real-time swell, wind direction, silent alarms.
    *   *Goal:* Reveal the physical manifestation of the belief.

## Structure

*   **`index.html`**: Semantic HTML5 markup.
*   **`styles.css`**: Custom CSS variables for a "Dark Mode" aesthetic (`#0a0a0a` background). Features scroll-triggered fade-in animations.
*   **`images/`**:
    *   `wooden_lamp.png`: The primary feature image.
    *   `black_lamp.png`, `blue_lamp.png`: Available assets for future gallery expansion.
    *   `three_lamps.png`: Group shot (currently unused).

## Local Development

To run the landing page locally:

```bash
cd landing_page
python3 -m http.server 8081
```

Then visit `http://localhost:8081`.

## Deployment

This page is deployed as a **Static Site** on Render.

*   **Service Name:** `surf-lamp-landing`
*   **Build Command:** `echo 'Static site'`
*   **Start Command:** `cd landing_page && python -m http.server $PORT`
*   **Root Directory:** `landing_page` (Recommended setting to avoid unnecessary rebuilds)
