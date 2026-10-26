---
name: skill-router
description: |
  Use when you need to find the most relevant skill for a task before acting. Causes you to check available skills against the task and pick the best match instead of guessing or skipping.
---

# Skill Router

**Core principle: check for relevant skills BEFORE acting on any task.**

This skill is a meta-skill — it helps you find OTHER skills that apply to what you're doing.

## The Problem

Without this skill, you:
- Skip checking for skills entirely
- Pick the wrong skill for the task
- Use skills inconsistently (some turns checked, others not)
- Miss skills that would've helped

## How to Use

When given any task, follow this sequence:

### Step 1: Extract the task type

Classify what kind of work this is:

| Task signal | Task category |
|---|---|
| "build X", "create feature", "let's make" | creative / implementation |
| "fix this bug", "it's broken", "error" | debugging |
| "how does X work", "research", "find info" | research / knowledge |
| "review this", "check my code" | code review |
| "test this", "write tests" | testing |
| "plan this", "design" | planning |
| "deploy", "setup", "install" | devops / infrastructure |
| "video", "edit", "render" | media / video |
| "post", "social", "outreach" | social media / outreach |
| "write a skill", "edit skill" | skill authoring |
| "multiple things", "parallel" | parallel dispatch |
| "before claiming done", "is it finished" | verification |

### Step 2: Search for matching skills

Use `skills_list()` to get all available skills, then filter by description match against the task category.

**Quick filter approach:**
```python
# Pseudocode — actual invocation:
all_skills = skills_list()  # get all available skills
relevant = [s for s in all_skills if task_keywords_match(s.description, task)]
```

**Keyword matching heuristics:**
- Implementation tasks → look for "build", "create", "implement", "feature"
- Debugging → look for "bug", "error", "debug", "fix"
- Research → look for "research", "find", "search", "investigate"
- Review → look for "review", "check", "audit"
- Testing → look for "test", "TDD", "write test"
- Planning → look for "plan", "design", "spec"
- DevOps → look for "deploy", "install", "setup", "configure"
- Media → look for "video", "render", "compose", "edit"
- Social → look for "post", "social", "outreach", "comment"
- Skill authoring → look for "skill", "writing"
- Multi-task → look for "parallel", "dispatch", "subagent"
- Verification → look for "verify", "completion", "done", "check"

### Step 3: Rank and select

For each candidate skill, score:

1. **Description match** — how closely does the skill's "Use when..." match the task?
2. **Process vs implementation** — process skills (brainstorming, debugging) should fire before implementation skills
3. **Specificity** — a skill that specifically addresses this task type beats a generic one

Pick the top 1-3 skills. More than 3 means you're not narrowing enough.

### Step 4: Invoke before acting

```
Using [skill-name] to [purpose]
```

Then follow the skill's instructions. If the skill has a checklist, create a todo per item.

### Step 5: If no skill matches

If no available skill matches the task:
- Check `superpowers:using-superpowers` — it covers the general case of "how to use skills"
- If the task is novel enough to warrant a new skill, use `superpowers:writing-skills` to create one
- Don't just skip skill-checking because nothing matched — document what you checked

## When NOT to Use

- **Subagent dispatch:** If you were dispatched as a subagent with a specific task, skip this — you already have a directive
- **Trivial status check:** "Is X running?" — no skill applies, just check
- **The task IS to find a skill:** then you're already using this skill

## Examples

**Task: "Fix the login bug"**
1. Task type: debugging
2. Search: skills with "bug", "error", "debug" in description
3. Match: `superpowers:systematic-debugging` (Phase 1 before any fix)
4. Invoke: "Using superpowers:systematic-debugging to find root cause before fixing"

**Task: "Build a React todo app"**
1. Task type: creative / implementation
2. Search: skills with "build", "create", "feature"
3. Match: `superpowers:brainstorming` first (before any code)
4. Invoke: "Using superpowers:brainstorming to explore approach before implementing"

**Task: "Deploy this to production"**
1. Task type: devops
2. Search: skills with "deploy", "setup", "install"
3. Match: platform-specific devops skill if available, otherwise check for generic deployment guidance
4. Invoke relevant skill

## Red Flags

These thoughts mean you're skipping the router:

| Thought | Reality |
|---|---|
| "I know what skill to use" | Verify it's available and loaded, not just remembered |
| "This is too simple for a skill check" | Simple tasks still get the router — it's fast |
| "I'll just start and check later" | Later skill-check never happens |
| "No skill will help with this" | You checked 0 skills to reach that conclusion |

**All of these mean: STOP. Run the router.**

## Integration

This skill is meant to be the FIRST check on every task. It should fire before:

- `superpowers:brainstorming` — for creative work (router finds brainstorming, then brainstorming runs)
- `superpowers:systematic-debugging` — for bugs (router finds debugging, then debugging runs)
- Any implementation skill — router finds the implementation skill, then it runs

The router doesn't replace other skills — it ensures you actually load the right one.
