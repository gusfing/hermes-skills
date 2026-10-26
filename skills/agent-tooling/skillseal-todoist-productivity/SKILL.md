---
name: skillseal-todoist-productivity
description: Todoist mastery — projects, tasks, priorities, labels, filters, recurring tasks, GTD, integrations, and productivity workflows. Use when setting up or optimizing a Todoist workspace, reviewing tasks, or implementing GTD/PARA in Todoist.
version: 1.0.0
author: Workloop
license: MIT
tags:
  - productivity
  - todoist
  - gtd
  - task-management
  - automation
---

# Todoist Productivity

Comprehensive guide to mastering Todoist for personal and team productivity. Covers project organization, task management, priority systems, labeling strategies, filters, recurring tasks, GTD implementation, and integrations.

## Projects

Projects are the top-level organizational unit in Todoist. They hold tasks and can be nested into a hierarchy.

### Project Organization Patterns

**PARA Method (Tiago Forte)**
- **Projects**: Active, outcome-driven efforts with a deadline. Example: "Launch website redesign" (due June 15).
- **Areas**: Ongoing responsibilities without end dates. Example: "Health", "Finances", "Professional Development".
- **Resources**: Reference material organized by topic. Example: "Design Inspiration", "Code Snippets".
- **Archives**: Inactive items from the other three categories. Move completed or abandoned projects here.

Use emoji-free, descriptive names for clarity. Prefix Areas with "Area:" and Resources with "Res:" if desired.

**GTD Setup (David Allen)**
- **Inbox**: Default capture point for all incoming tasks. Process to zero daily.
- **Next Actions**: Tasks that can be done now, organized by context.
- **Waiting For**: Tasks delegated or blocked on external input.
- **Projects**: Outcomes requiring more than one action step.
- **Someday/Maybe**: Ideas not yet committed to.
- **Reference**: Non-actionable information.

**Team Projects**
Shared projects appear with a team icon. Use comments for async communication on tasks. Assign tasks to team members with the "+" syntax or the assignee picker.

### Project Hierarchy

Todoist supports up to 4 levels of nesting. A parent project can contain child sub-projects. Use this for:
- Department > Team > Initiative
- Life Area > Sub-Area > Specific Project

Avoid overly deep nesting — 3 levels maximum for usability. Deeply nested projects become invisible in filters and search.

### Project Best Practices

- Keep active projects under 10-15. Archive completed projects aggressively.
- Use project colors sparingly for visual scanning — one color per life area.
- Pin frequently accessed projects to the top of the sidebar.
- Review project list weekly during your Weekly Review.

## Tasks

Tasks are the atomic unit of work in Todoist. Every task should represent a single, concrete action.

### Task Creation

Use natural language for fast entry:
```
"Submit expense report tomorrow at 10am p1 @office #Finance"
```
This creates a task named "Submit expense report", due tomorrow at 10:00, priority 1, with label @office, in the Finance project.

### Natural Language Parsing

Todoist parses the following from task names:
- **Dates**: "today", "tomorrow", "next Monday", "Jan 15", "in 3 days", "every weekday"
- **Times**: "at 10am", "at 14:00", "at noon"
- **Priorities**: "p1", "p2", "p3", "p4" (or !!, !, none)
- **Projects**: "#ProjectName" moves the task to that project
- **Labels**: "@labelname" applies a label
- **Assignees**: "+personname" assigns to a collaborator

Always type the date/time before the project and labels — Todoist parses left to right and stops at unrecognized tokens in some contexts.

### Subtasks

Subtasks break a parent task into smaller steps. Two behaviors:
- **Default**: Subtasks are independent tasks that happen to be nested. Completing them does not complete the parent.
- **Section-style**: Use uncompleteable parent tasks as section headers by not giving them a due date.

Best practice: Use subtasks for checklists (e.g., packing list, onboarding steps). Use separate tasks in a project for sequential workflow steps.

### Sections

Sections divide a project into visual groups. Common section patterns:
- **Kanban**: "Backlog", "This Week", "In Progress", "Done"
- **GTD**: "Next Actions", "Waiting For", "Reference"
- **Timeline**: "Phase 1", "Phase 2", "Phase 3"
- **Workflow**: "To Do", "Doing", "Review", "Done"

Sections are cosmetic only — they do not affect filters or queries. Use labels if you need queryable groupings.

### Task Hygiene

- One action per task. "Research venues AND book caterer" should be two tasks.
- Start every task with a verb: "Call", "Review", "Write", "Buy", "Schedule".
- Add context in the task description field, not the task name. Keep names short.
- Use the description for links, notes, checklists, and reference material.
- If a task takes less than 2 minutes, do it immediately rather than adding it to Todoist (the "two-minute rule" from GTD).

## Priorities

Todoist uses four priority levels, color-coded and filterable.

| Priority | Color | Shortcut | Use Case |
|----------|-------|----------|----------|
| p1 (urgent) | Red | `!!` or `p1` | Must do today. Consequences if missed. |
| p2 (high) | Orange | `!` or `p2` | Should do today. Important but not urgent. |
| p3 (medium) | Blue | `p3` | Default priority. Nice to do. |
| p4 (low) | None | `p4` | Optional. No deadline pressure. |

### Priority Strategy

- **Limit p1 tasks to 3 per day**. More than 3 urgent tasks means everything is urgent, which means nothing is.
- Use p2 for your "big rocks" — the important-but-not-urgent work from the Eisenhower Matrix. This is where long-term value lives.
- p3 is the default and should be the bulk of your task list.
- p4 is for stretch goals, nice-to-haves, and low-consequence items.
- Re-evaluate priorities during your Weekly Review. p1 tasks that linger for days are not truly p1.

### Priority in Filters

```
p1 & today          # Urgent tasks due today
p1 & no date        # Urgent tasks without deadlines (review these)
p2 & overdue        # High-priority overdue items
(p1 | p2) & today   # All high and urgent tasks due today
```

## Labels

Labels add metadata to tasks, enabling powerful filtering and organization beyond projects.

### Context Labels (GTD-inspired)

Label tasks by the context required to complete them:
- `@home` — Requires being at home
- `@office` — Requires being at the office
- `@errands` — Requires being out and about
- `@computer` — Requires a computer (online work)
- `@phone` — Can be done from a phone (calls, quick messages)
- `@anywhere` — Can be done from anywhere

### Energy and Time Labels

- `@deep_work` — Requires focused, uninterrupted time (90+ minutes)
- `@shallow` — Low-cognitive-load tasks (email, admin, data entry)
- `@5min`, `@15min`, `@30min`, `@60min` — Time estimates
- `@high_energy` — Best done when mentally fresh
- `@low_energy` — Can be done when tired

### Status Labels

- `@waiting` — Blocked on someone else (alternative to a Waiting For project)
- `@delegated` — Assigned to someone else but you are tracking it
- `@next` — Your next action for a project (useful across projects)
- `@someday` — Not committed yet (alternative to Someday/Maybe project)

### Meta Labels

- `@review` — Needs attention during Weekly Review
- `@stale` — Has not been touched in 2+ weeks
- `@blocked` — Cannot proceed due to an external dependency
- `@idea` — Not yet a concrete task, needs refinement

### Label Best Practices

- Limit to 15-20 active labels. Too many labels creates decision fatigue.
- Use consistent naming. Pick `@home` or `@house` and stick with it.
- Review label usage monthly. Remove labels that are not filtering anything.
- Combine context + energy labels: `@computer & @deep_work` finds focused computer tasks.

## Filters

Filters (custom views) are Todoist's most powerful feature. They combine projects, labels, priorities, and dates into saved queries.

### Filter Syntax

| Operator | Meaning | Example |
|----------|---------|---------|
| `&` | AND | `today & p1` |
| `\|` | OR | `@home \| @office` |
| `!` | NOT | `!@waiting` |
| `()` | Grouping | `(p1 \| p2) & today` |
| `#` | Project | `#Work` |
| `##` | Sub-project | `##Team` |
| `@` | Label | `@computer` |
| `assigned to:` | Assignee | `assigned to: me` |
| `overdue` | Past due date | `overdue` |
| `no date` | No due date set | `no date` |
| `no label` | No labels applied | `no label` |
| `search:` | Text search | `search: budget` |
| `created:` | Creation date | `created: before -7 days` |
| `/` | Section | `#Project / Section` |

### Essential Filters

**Daily Focus**
```
(p1 | p2) & today
```
Shows all high-priority tasks due today. Start your day here.

**Weekly Review**
```
(p1 & no date) | overdue | @review
```
Catch-all for tasks needing attention: urgent without dates, overdue items, flagged for review.

**By Context**
```
@phone & !@waiting
```
Phone calls you can make now, excluding anything blocked.

**Energy-Matched**
```
@deep_work & (today | overdue)
```
Deep work tasks that need attention now.

**Waiting For**
```
@waiting & 30 days
```
Everything you are waiting on, scoped to the last 30 days to keep the list manageable.

**No Project**
```
#Inbox & !@someday
```
Inbox items that are not intentionally parked in Someday. Process these.

**Stale Tasks**
```
created before: -14 days & !@someday & !@waiting & no date
```
Tasks older than 14 days with no due date and no status label. These need a decision.

**Today's Summary**
```
today | overdue
```
Everything due or past due.

### Filter Best Practices

- Name filters with action-oriented titles: "Morning Review", "Calls to Make", "Weekend Errands".
- Add filters to favorites (star them) for quick access.
- Review your filter list monthly. Remove unused filters.
- Use `assigned to: me` in shared projects to see only your work.
- The `search:` operator matches task names, descriptions, and comments. Use it for keyword-based views.

## Recurring Tasks

Todoist parses natural language recurrence patterns when setting due dates.

### Recurrence Syntax

| Pattern | Example | Result |
|---------|---------|--------|
| `every day` | "every day at 8am" | Daily at 8am |
| `every week` | "every Monday" | Weekly on Monday |
| `every month` | "every 15th" | Monthly on the 15th |
| `every year` | "every Jan 1" | Annually |
| `every X days` | "every 3 days" | Every 3 days from completion |
| `every! day` | "every! day" | Every day, even if overdue (strict recurrence) |
| `every weekday` | "every weekday at 9am" | Monday through Friday |
| `every other week` | "every other Monday" | Biweekly |
| `every last day` | "every last day" | Last day of every month |
| `every first Mon` | "every first Mon" | First Monday of every month |
| `starting` | "every day starting Jan 1" | Recurrence begins on a future date |
| `ending` | "every weekday ending Dec 31" | Recurrence stops on a date |

### Recurring Task Strategies

- **Habits**: Use `every! day` for daily habits you want to show up regardless of whether you completed yesterday's instance. The exclamation mark forces strict scheduling.
- **Chores**: Use `every 7 days after completion` for tasks like "Clean fridge" — the clock resets from the day you actually do it, not from a fixed schedule.
- **Reviews**: "every month" for monthly budget review, "every Monday" for weekly team standup prep.
- **Maintenance**: "every 3 months" for car service reminders, "every 6 months" for dental checkup.

### Recurring Task Pitfalls

- Recurring tasks with subtasks: Completing the parent reschedules it and resets subtasks. Use project templates instead for complex recurring workflows.
- Over-recurrence: If you consistently postpone a recurring task, the frequency is wrong. Adjust it.
- Strict vs. flexible: `every! Monday` creates a task every Monday regardless. `every Monday` only creates the next one after you complete the current one. Choose based on whether missing one means it should be skipped entirely.

## GTD in Todoist

Getting Things Done (David Allen) maps cleanly to Todoist.

### The GTD Workflow

1. **Capture**: Everything goes into the Inbox. Use Todoist quick-add (global shortcut: Ctrl+Shift+A / Cmd+Shift+A) to capture ideas, tasks, and commitments without breaking flow.

2. **Clarify**: Process Inbox to zero. For each item ask: Is it actionable?
   - **No**: Trash, reference, or Someday/Maybe.
   - **Yes**: What is the next action? If under 2 minutes, do it now. Otherwise, delegate it or defer it.

3. **Organize**: Move clarified items into the right places:
   - Next Actions project with context labels (@phone, @computer)
   - Waiting For project with @waiting label
   - Project-specific tasks with deadlines
   - Calendar for time-specific commitments

4. **Reflect**: Weekly Review. Go through:
   - Inbox to zero
   - Review project list — is every project moving?
   - Review calendar — upcoming deadlines and commitments
   - Review Waiting For — follow up on stale items
   - Review Someday/Maybe — anything to activate?

5. **Engage**: Use context-based filters to see only what you can do right now:
   ```
   @phone & !@waiting    # Calls when you have phone time
   @computer & @deep_work # Focused computer work
   @errands & today      # Errands to run today
   ```

### GTD Project Structure in Todoist

```
Inbox
Next Actions
  / Calls
  / Computer
  / Errands
  / Home
  / Office
Waiting For
Projects
  Project A
  Project B
Someday/Maybe
Reference
```

Alternatively, use a single "Next Actions" project with context labels instead of sections. This is more flexible with filters.

## Integrations

### Calendar Integration

- **Google Calendar / Outlook**: Two-way sync. Tasks with due dates and times appear on your calendar. Calendar events do not become tasks. Use this for time-blocking your p1 and p2 tasks.
- **Fantastical**: Native Todoist integration on Mac/iOS. Tasks appear alongside calendar events.
- **Strategy**: Only sync tasks with actual time commitments. Do not sync your entire task list to the calendar.

### Email to Task

- **Todoist Plugin for Gmail/Outlook**: Turn emails into tasks with one click. The task includes a link back to the original email.
- **Forward to Todoist**: Forward emails to your unique Todoist inbox address. The subject becomes the task name, the body becomes the description.
- **Strategy**: Use for actionable emails. If the email is reference material, save it elsewhere (notion, obsidian, drive).

### Automation and IFTTT/Zapier/Make

- **IFTTT**: Connect Todoist to hundreds of services. Common recipes: "Starred email in Gmail becomes a task", "Completed task logs to Google Sheet".
- **Zapier**: Multi-step automation. "New Trello card creates a Todoist task", "Completed Todoist task sends a Slack message".
- **Make (Integromat)**: Visual automation builder. More flexible than Zapier for complex workflows.
- **Todoist API**: RESTful API for custom integrations. Use the official Python client (`todoist-api-python`) for programmatic task management.

### Other Integrations

- **Slack**: `/todoist add [task]` creates a task from Slack. Notifications for task assignments.
- **Alfred / Raycast**: Quick-add tasks from the desktop launcher.
- **Shortcuts (iOS) / Tasker (Android)**: Mobile automation hooks.
- **Toggl / Clockify**: Time tracking integration for tasks.
- **Pleexy**: Bidirectional sync with Evernote, OneNote, Notion, and other note apps.

## Productivity Workflows

### Daily Workflow

1. **Morning Review (5 min)**: Open "Today's Summary" filter. Adjust priorities. Move non-essential tasks to another day.
2. **Time-Block**: Assign times to your p1 tasks. Schedule deep work blocks. Leave gaps for interruptions.
3. **Work from Filters**: Use context filters throughout the day:
   - Morning: `@deep_work & today` for focused output
   - Afternoon: `@shallow & today` for admin and communication
   - End of day: `@phone & today` for calls
4. **Evening Review (3 min)**: Check off completed items. Reschedule anything not finished. Add tomorrow's tasks. Clear inbox.

### Weekly Review (30-45 min)

1. Process Inbox to zero
2. Review each active project — is there a next action?
3. Review calendar for the coming week — add prep tasks
4. Review Waiting For list — follow up as needed
5. Review Someday/Maybe — activate or delete
6. Review labels and filters — clean up unused ones
7. Set 3-5 key objectives for the week

### The "Do It Tomorrow" Rule

At the end of the workday, if a task is not completed and is not a true p1, reschedule it to tomorrow. Do not carry a long overdue list — it creates psychological weight and reduces trust in your system.

### Task Batching

Group similar tasks and execute them in a single session:
- **Calls batch**: All @phone tasks done in one 30-minute block
- **Email batch**: Process email twice a day, not continuously
- **Errand batch**: All @errands tasks grouped geographically

## Common Pitfalls

1. **Too many p1 tasks**: If everything is urgent, nothing is. Limit to 3 p1 per day.
2. **Overdue accumulation**: An overdue list longer than 5 items means your system is broken. Reschedule or delete.
3. **Inbox neglect**: Inbox should hit zero daily. An overflowing inbox is a capture system, not a task system.
4. **Project proliferation**: Creating a project for every idea. Use Someday/Maybe instead. Active projects should fit on one screen.
5. **Label overload**: More than 20 labels becomes unmanageable. Audit and prune regularly.
6. **No Weekly Review**: The system breaks without regular maintenance. Schedule it like any other appointment.
7. **Wrong granularity**: Tasks that are too big ("Launch business") or too small ("Open laptop"). One concrete action per task.
8. **Ignoring energy**: Assigning deep work tasks to low-energy time slots. Match task type to energy level.

## References

- *Getting Things Done* by David Allen
- *The PARA Method* by Tiago Forte
- Todoist official documentation: https://todoist.com/help
- Todoist API reference: https://developer.todoist.com/rest/v2/
- Todoist integration directory: https://todoist.com/integrations
