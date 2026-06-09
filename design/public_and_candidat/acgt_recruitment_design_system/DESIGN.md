---
name: ACGT Recruitment Design System
colors:
  surface: '#fbf8ff'
  surface-dim: '#dbd9e1'
  surface-bright: '#fbf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f2fb'
  surface-container: '#efecf5'
  surface-container-high: '#eae7ef'
  surface-container-highest: '#e4e1ea'
  on-surface: '#1b1b21'
  on-surface-variant: '#454652'
  inverse-surface: '#303036'
  inverse-on-surface: '#f2eff8'
  outline: '#767683'
  outline-variant: '#c6c5d4'
  surface-tint: '#4c56af'
  primary: '#000666'
  on-primary: '#ffffff'
  primary-container: '#1a237e'
  on-primary-container: '#8690ee'
  inverse-primary: '#bdc2ff'
  secondary: '#525f71'
  on-secondary: '#ffffff'
  secondary-container: '#d3e1f6'
  on-secondary-container: '#566475'
  tertiary: '#380b00'
  on-tertiary: '#ffffff'
  tertiary-container: '#5c1800'
  on-tertiary-container: '#e17c5a'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e0e0ff'
  primary-fixed-dim: '#bdc2ff'
  on-primary-fixed: '#000767'
  on-primary-fixed-variant: '#343d96'
  secondary-fixed: '#d6e4f9'
  secondary-fixed-dim: '#bac8dc'
  on-secondary-fixed: '#0f1c2c'
  on-secondary-fixed-variant: '#3a4859'
  tertiary-fixed: '#ffdbd0'
  tertiary-fixed-dim: '#ffb59d'
  on-tertiary-fixed: '#390c00'
  on-tertiary-fixed-variant: '#7b2e12'
  background: '#fbf8ff'
  on-background: '#1b1b21'
  surface-variant: '#e4e1ea'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 57px
    fontWeight: '700'
    lineHeight: 64px
    letterSpacing: -0.25px
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
  headline-md:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-sm:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-lg:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: '500'
    lineHeight: 28px
  title-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 24px
    letterSpacing: 0.15px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0.5px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0.25px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.1px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.5px
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  margin-mobile: 16px
  margin-desktop: 24px
  gutter: 16px
  container-max-width: 1200px
---

## Brand & Style
The design system for the Agence Congolaise des Grands Travaux (ACGT) is built on the pillars of **authority, transparency, and institutional trust**. As a public recruitment platform, the UI must balance the gravitas of a government agency with the accessibility of a modern digital product.

The visual style follows a **Modern Corporate** aesthetic, heavily influenced by Material Design 3 principles but refined for professional recruitment. It utilizes structured elevation, generous whitespace to reduce cognitive load during application processes, and a clear visual hierarchy that guides candidates through complex forms. The emotional response should be one of reliability and officiality, ensuring citizens feel their data is secure and their applications are being processed with institutional integrity.

## Colors
The palette is rooted in **Midnight Blue**, symbolizing the stability of the state. This is supported by **Deep Navy** for depth and gradients, creating a sophisticated professional environment.

- **Primary (Midnight Blue):** Used for navigation headers, primary actions, and brand reinforcement.
- **Accent (Yellow):** Reserved strictly for Call-to-Action (CTA) elements. It must always be paired with dark text (Deep Navy) to ensure AAA accessibility standards.
- **Background & Surface:** A crisp "Very Light Gray" background contrasts with pure white surfaces to create clear containment for data-heavy sections.
- **Semantic Colors:** Used for application status indicators (e.g., "En attente," "Approuvé," "Rejeté").

## Typography
The system uses **Inter** exclusively for its exceptional legibility and neutral, modern character. 

- **Headings:** Bold weights are used for page titles and section headers to establish authority and clear scanning.
- **Content:** Medium and Regular weights ensure high readability for long-form job descriptions and legal requirements.
- **Language:** All typography must support French character sets (accents and special characters).
- **Scale:** For mobile devices, `headline-lg` scales down to 28px to maintain visual balance on smaller viewports.

## Layout & Spacing
This design system utilizes a **12-column fluid grid** for desktop and a **4-column grid** for mobile.

- **Rhythm:** An 8px linear scale governs all spacing.
- **Margins:** 24px margins on desktop provide room for the content to breathe, while 16px margins on mobile maximize the limited horizontal space.
- **Reflow:** Components like data tables should transform into stacked cards on mobile devices to maintain usability. 
- **Containers:** Content is housed in a max-width container (1200px) to prevent excessively long line lengths on ultra-wide monitors, preserving readability for job postings.

## Elevation & Depth
In line with Material Design 3, depth is conveyed through **Tonal Layers** and **Soft Shadows**.

- **Level 0 (Background):** Very Light Gray (#F5F7FA), flat.
- **Level 1 (Cards/Surface):** White (#FFFFFF) with a 1px border (#E0E4E9) and no shadow for low-priority content.
- **Level 2 (Elevated):** White with a soft, diffused shadow (Blur: 8px, Y: 4px, Opacity: 0.05, Color: Midnight Blue) to indicate interactive elements like job cards.
- **Level 3 (Modals/Overlays):** Higher elevation with more prominent shadows to pull the element forward from the background.

## Shapes
The shape language is modern and approachable. A standard **16px (1rem) corner radius** is applied to primary UI containers like cards, input fields, and buttons.

- **Small Components:** Chips and small buttons use a 12px or fully rounded (pill) radius.
- **Large Components:** Main content containers and modals use the standard 16px radius.
- **Borders:** When used, borders are 1px thick and tinted with a neutral grey-blue to maintain a soft but defined structure.

## Components
- **Buttons:** 
  - *Primary:* Yellow (#FDD835) with Deep Navy text, 16px radius, bold weight.
  - *Secondary:* Midnight Blue with White text.
  - *Outlined:* Midnight Blue border and text, transparent fill.
- **Chips:** Used for status (e.g., "Ouvert," "Clôturé"). These are elevated slightly with high-contrast text and low-opacity background tints of the semantic colors.
- **Cards:** 16px rounded corners, 1px subtle border, and Level 2 elevation on hover. Content inside cards should follow the 16px padding rule.
- **Input Fields (Vuetify style):** Outlined fields with Midnight Blue focus states. Labels are always visible or float upon focus.
- **Steppers:** Used for multi-step applications. Numbers are housed in Midnight Blue circles, with progress indicated by a horizontal line.
- **Data Tables:** Clean, no vertical borders. Headers in Deep Navy with bold text. Alternating row highlights (zebra striping) using a very faint gray.
- **Identity:** The ACGT logo should always be placed in the top-left of the navigation bar, adhering to the 24px margin rule.