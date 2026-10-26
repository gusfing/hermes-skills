---
name: ian-xiaohei-illustrations
description: Generate Ian Xiaohei illustrations. Hand-drawn, white, 16:9.
---
# Ian Xiaohei Weird Article Illustrations

## Core Position

Design and generate 16:9 horizontal article illustrations for English-language content. Turn the article's key judgments, workflows, structures, states, or metaphors into a clean, weird, creative hand-drawn explainer that reads clearly without looking like a manual.

Default visual IP: Xiaohei, a black solid creature with white dot eyes, thin legs, a blank expression, and a serious but absurd attitude. Xiaohei must participate in the core action of the image, not stand at the side as decoration.

All handwritten annotations and labels on the image should be in English.

## Style DNA

**Must-Haves:**
- 16:9 horizontal body illustration
- Pure white background: no beige, warm gray, paper texture, gradients, shadows, noise, or retro paper feel
- Black hand-drawn line art as the base: thin lines, slight wobble, not mechanical, not vector, not heavy outlines
- Lots of empty space: subject takes ~40-60% of frame, at least 35% blank area, ideally one large quiet zone
- Sparse English handwritten annotations: at most 5-8 total, each 1-5 short words
- One image explains only one core action, structure, state, or metaphor

**Color Palette:**
- Black: primary line art, characters, frames, structures, main text, main objects
- Red: key annotations, problems, emotional points, critical reminders, results
- Orange: main flow, paths, arrows, automation flow, movement from A to B
- Blue: side notes, mental state, system state, second-layer explanation, AI/assistant/automation cues

**Absolute No:**
- No commercial illustration, PPT infographic, formal flowchart, course slide
- No cute cartoon poster, children's illustration, complex architecture diagram
- No polished flat illustration, tech UI look, real app screenshot
- No complex background, gradients, shadows, or texture
- No top-left titles like "Workflow", "System Architecture", "Common Pitfalls", "Route Map"

## Xiaohei IP

**Appearance:**
- Black solid little monster
- White dot eyes
- Thin legs, sometimes thin arms
- Body: cylinder, bean, box, funnel, shadow, hole, or black chunk inside a machine
- Slightly irregular outline with hand-drawn feel
- Expression: blank, dull, calm, serious

**Personality:**
- Serious but absurd
- Low-key system operator
- Dry humor, not cute
- A little clumsy but not dumb
- Real worker in a whiteboard sketch

**Common Roles (Xiaohei performs core action):**
- Carry materials, pull lines to gather information sources
- Get stuck at a breakpoint, operate a "decision" lever inside a machine
- Become a filtering funnel, cut open a "material fish"
- Stamp a handoff phrase, pull a handoff path
- Hold up a warning sign to point out pitfalls
- Reach out from a hole but fail to catch content
- Carry bricks, build bridges, open doors, sort, record

**Rule:** If removing Xiaohei still leaves the core metaphor intact, Xiaohei is too decorative.

## Composition Patterns

Structure types (pick one per image):
1. **Two Breakpoints** - Input → Breakpoint 1 → Process → Breakpoint 2 → Output
2. **Sort by Purpose** - One input, multiple sorted outputs by criteria
3. **One Fish Many Uses** - Single core element, multiple derivative uses
4. **Handoff Path** - A → B → C with clear handoff points
5. **Information Well** - Deep extraction from noisy source
6. **Idea Press** - Compression of raw input into refined output
7. **Content Fermentation** - Time-based transformation
8. **Trust Bridge** - Connecting two separated elements

## Generation Workflow

1. **Digest** - Extract core idea, cognitive turns, visualizable parts
2. **Shot List** - Plan 4-8 images (default 3), each with placement, topic, structure type, Xiaohei action, labels
3. **Generate** - One image at a time via image_gen with 16:9 prompt
4. **QA Check** - Verify against qa-checklist.md
5. **Save** - Copy to workspace/assets/<slug>-illustrations/

## Prompt Template

```
16:9 horizontal English article illustration, pure white background, black hand-drawn line art, thin wobbly lines, lots of empty white space (40-60% subject, 35%+ blank). Xiaohei (black solid creature, white dot eyes, thin legs, blank serious expression) as core action subject: [XIAOHEI_ACTION]. Sparse English handwritten annotations (max 5-8, 1-5 words each): [LABELS in red/orange/blue]. No titles, no PPT look, no commercial illustration, no cute cartoon, no gradients/shadows/texture. Weird, creative, clean, slightly unhinged product-sketch feel.
```