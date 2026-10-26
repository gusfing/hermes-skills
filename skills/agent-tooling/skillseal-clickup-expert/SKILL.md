---
name: skillseal-clickup-expert
description: Use when working with ClickUp — setting up, auditing, or optimizing workspaces. Covers hierarchy (Spaces/Folders/Lists/Tasks), custom fields, views, automations, status workflows, Docs, integrations, and API fundamentals.
version: 1.0.0
author: Workloop
license: MIT
---

# ClickUp Expert

Comprehensive reference for ClickUp — the converged AI workspace for project management, docs, goals, chat, and automation. This skill covers workspace structure, configuration patterns, and best practices validated against real-world ClickUp deployments.

## Hierarchy

The ClickUp hierarchy is the backbone of all organization. Every item nests inside the layer above it.

```
Workspace
  Space
    Folder
      List
        Task
          Subtask (up to 7 levels of nesting when the Nested Subtasks ClickApp is enabled)
```

### Workspace

The top-level organizational unit. Represents an entire company, account, or organization. In API v2 this was called "Team"; API v3 uses "Workspace" consistently. A workspace contains all Spaces.

### Spaces

Sit directly under a Workspace. Think of these as departments, teams, or major areas of focus. Each Space can have its own:

- Custom statuses
- Custom fields
- ClickApps (Sprints, Time Tracking, Priorities, Tags, etc.)
- Permission settings (private, shared with individuals or teams)

Common Space patterns:

- **Marketing** — Folders for SEO, Content, Paid Advertising, Social Media
- **Development** — Folders for Frontend, Backend, UI/UX, DevOps
- **Operations** — Folders for HR, Finance, Legal, IT
- **Delivery / Clients** — Folders per client, each with Lists for projects/retainers
- **Personal** — Folders for Travel, Health, Finance, Hobbies

### Folders

Live inside Spaces. Group related Lists together. Think of them as categories or project containers. Folders can contain Lists and Subfolders. Use folders to:

- Group projects by campaign, quarter, or initiative
- Separate client work (one folder per client)
- Organize departmental functions

When to use Folders vs. going straight to Lists:
- **Use Folders** for medium-to-large projects with multiple workstreams, or when you need a grouping layer between the Space and Lists
- **Skip Folders** for simple Spaces where a single List is enough

### Lists

Contain tasks and are the primary work management unit. Lists can sit inside Spaces, Folders, or Subfolders. Each List has its own:

- Views (List, Board, Calendar, Gantt, etc.)
- Statuses (inherited from Space/Folder or overridden)
- Custom fields
- Automations

Common List patterns:

- **Single-project List** — one List per project with tasks as deliverables
- **Sprint List** — backlog managed in a regular List alongside Sprint folders
- **CRM List** — each task is a contact or deal
- **Process List** — recurring workflow (onboarding, content calendar, invoice processing)

### Tasks

The fundamental work item. Each task has:

- Name and description (rich text with markdown support)
- Assignees (single or multiple)
- Status (from the List/Folder/Space workflow)
- Priority (Urgent, High, Normal, Low, None)
- Start and due dates
- Time estimates and tracked time
- Custom field values
- Comments, attachments, Checklists
- Subtasks (nested up to 7 levels with the ClickApp enabled)
- Relationships (linked tasks and Docs)
- Dependencies (blocking, waiting on, etc.)

Task sizing standard:

- **Small (single-person)** — one List, tasks with subtasks for individual work
- **Medium (team collaboration)** — folder per project, Lists per workstream
- **Large (multi-team)** — folder per project, Lists per stage/team, subtasks for detailed work

## Views

ClickUp offers 15+ views that render the same underlying task data differently. Views can be created at any hierarchy level (Space, Folder, List, or Everything level).

### Core Views

| View | Use Case |
|---|---|
| **List** | Spreadsheet-style row view; sort, filter, group by any field. Default for most workflows. |
| **Board** | Kanban-style columns grouped by status. Drag tasks between columns. Ideal for agile/sprint work. |
| **Calendar** | Tasks on a calendar by due date. Drag to reschedule. Best for deadline-driven work and content calendars. |
| **Gantt** | Timeline with dependency arrows. Shows critical path, delays, bottlenecks. Exportable as PDF. |
| **Table** | Spreadsheet with column customization, formula-like calculations, and bulk editing. |
| **Timeline** | Linear schedule view. See who is working on what across days/weeks/months. |
| **Workload** | Capacity view showing assigned work vs. available time per person. Flags overloads by day, week, or month. |
| **Box** | High-level sprint/agile view showing what each person is working on in a matrix layout. |
| **Activity** | Audit-log view of all actions in a location. Great for managers tracking progress. |
| **Team** | Shows each team member's tasks, completed work, and capacity. Useful for weekly reviews. |
| **Map** | Geographic map plotting tasks with Location custom fields. |
| **Mind Map** | Visual brainstorming view; nodes represent tasks, draggable to reorganize structure. |
| **Chat** | Conversation view for a location. Threaded discussions alongside tasks. |
| **Embed** | Embed external URLs, spreadsheets, videos alongside task data. |
| **Form** | Build custom forms that create tasks on submission. Useful for intake, requests, bug reports. |

## Custom Fields

Custom Fields add structured, queryable metadata to tasks. Available types:

- **Text** — free-form short text
- **Long Text** — multi-line text area
- **Dropdown** — single-select from predefined options
- **Multi-Select Dropdown** — multiple values from predefined options
- **Number** — numeric value with optional formatting
- **Currency** — monetary value with currency symbol
- **Date** — date picker without time
- **Email** — validated email address
- **Website** — validated URL
- **Phone** — phone number
- **Location** — address or coordinates (powers Map view)
- **Labels** — colored tags
- **Checkbox** — boolean true/false
- **Rating** — 1-5 star scale
- **Progress** — percentage bar (manual or auto-rollup from subtasks)
- **People** — link to ClickUp users
- **Task Relationship** — link to another task
- **File** — file attachment as field
- **AI Fields** — auto-generated summaries, translations, or custom AI prompts

Custom Fields can be added at the Space, Folder, or List level. Adding a field to Everything level applies it workspace-wide.

### Status vs. Custom Field Pattern

A common anti-pattern: using too many statuses to represent stages. Instead:

1. Keep statuses simple: **To Do / In Progress / Done** (or **Open / In Progress / Review / Complete**)
2. Use a **Dropdown Custom Field** (e.g., "Stage") for sub-statuses: Draft, Review, Approved, Published
3. Use Automations to keep the two in sync (e.g., when Stage = "Published" then Status = "Complete")

## Automations

ClickUp Automations follow a **Trigger + Condition(s) + Action** model. Available at Space, Folder, and List levels.

### Trigger Types

- Task created, updated, moved, or deleted
- Status changes
- Due date arrives or is approaching
- Priority changes
- Custom field value changes
- Checklist completed
- Time tracked
- Comment posted

### Action Types

- Change status
- Set/clear custom field value
- Assign task
- Set due date
- Move task to another List
- Post comment
- Apply template
- Add tags
- Send email
- Create subtask
- Webhook (call external URL)

### Best Practices

1. **Name automations descriptively** — include trigger and action in the name
2. **Use conditions to narrow scope** — filter by custom field values, task name patterns, or assignee
3. **Gate completion automations** — don't set status to Complete based on a field alone; verify subtasks or checklists are done
4. **Combine with Custom Fields** — Custom Fields provide the structured data that makes automations precise
5. **Test with a single task first** — verify the automation chain before enabling broadly

## Status Workflows

Statuses are customizable at every hierarchy level. A Space can define a default set of statuses; Folders and Lists can inherit or override them.

### Status Types (System)

- **Active** — task is being worked on (e.g., In Progress, Review, Blocked)
- **Done** — task is complete and closed
- **Closed** — task is closed but not complete (e.g., Duplicate, Won't Do)

### Recommended Starter Workflows

**Simple (personal/small team):**
- To Do -> In Progress -> Done

**Standard (team projects):**
- Open -> In Progress -> Review -> Complete

**Development (agile):**
- Backlog -> To Do -> In Progress -> Code Review -> QA -> Done

**Content/Marketing:**
- Idea -> Draft -> Review -> Approved -> Published

### Status Tips

- Keep status counts under ~10 per workflow to prevent confusion
- Mark "Done" statuses with the "Done" type so they show as complete
- Use "Closed" type for cancelled or duplicate tasks to keep them out of active views
- Combine with a "Stage" custom field for granular tracking without bloating statuses

## Docs

ClickUp Docs are collaborative, real-time documents integrated directly into the workspace hierarchy. They replace standalone tools like Notion, Confluence, or Google Docs.

### Key Features

- **Rich content blocks** — headings, tables, code blocks, checklists, embeds, columns
- **Nested pages and subpages** — organize documentation hierarchically
- **Real-time collaboration** — multi-user editing with visible cursors
- **Relationships** — link Docs to tasks and other Docs
- **Mentions** — reference tasks, Docs, and users inline with @mentions
- **Version history** — review and restore previous versions
- **Wikis** — mark any Doc as a wiki to designate it as the source of truth
- **Permissions** — control access at the Doc and page level
- **Templates** — save and reuse Doc structures

### Common Use Cases

- Company wiki and onboarding guides
- Project specifications and design docs
- Meeting notes linked to project tasks
- SOPs and process documentation
- Client-facing knowledge bases

### Doc-Task Workflow

1. Create a Doc for a project spec or plan
2. Link it to related tasks via Relationships
3. Mention tasks within the Doc for traceability
4. Tasks reference the Doc, creating bidirectional navigation

## Integrations

ClickUp offers native integrations, 1,000+ partner connectors, and a public REST API for custom integrations.

### Native Integrations

| Category | Tools |
|---|---|
| **Communication** | Slack, Microsoft Teams, Zoom, Discord |
| **Calendar** | Google Calendar, Outlook Calendar |
| **File Storage** | Google Drive, Dropbox, OneDrive, Box |
| **Development** | GitHub, GitLab, Bitbucket |
| **Design** | Figma, Loom, Vimeo, YouTube |
| **Time Tracking** | Toggl, Harvest, Clockify, Everhour, Timing, Rize |
| **CRM & Support** | HubSpot, Salesforce, Zendesk, Intercom |
| **Automation** | Zapier, Make (Integromat), Unthread |

### GitHub Integration (example)

- Link commits, pull requests, and branches to ClickUp tasks
- Change ClickUp task statuses from GitHub commit messages using task IDs
- View GitHub activity history directly in the task

### Slack Integration (example)

- Create tasks from Slack messages with `/clickup new`
- Unfurl task links with rich previews and quick actions
- Receive task notifications in channels

### API

- REST API v2 (`/api/v2/`) — uses "Team" for workspace
- REST API v3 (`/api/v3/`) — uses "Workspace" consistently; current recommended version
- Authentication via personal API token or OAuth 2.0
- Endpoints for: Workspaces, Spaces, Folders, Lists, Tasks, Custom Fields, Docs, Goals, Chat, Attachments, Time Tracking, Webhooks

## ClickApps

35+ optional features that can be enabled per Space. Key ClickApps:

- **Nested Subtasks** — subtasks up to 7 levels deep
- **Sprints** — agile sprint management with points, velocity, and burndown charts
- **Time Tracking** — manual and real-time timers on tasks
- **Time Estimates** — estimated hours per task; powers Workload view
- **Custom Fields** — structured metadata
- **Tags** — flexible cross-cutting labels
- **Priorities** — Urgent/High/Normal/Low/None
- **Dependencies** — task relationships (blocking, waiting on, linked)
- **Milestones** — special task type for key dates
- **Checklists** — sub-task lists within a task
- **Email in ClickUp** — send/receive email from tasks
- **Proofing** — annotate images and PDFs for review

## Workspace Setup Best Practices

1. **Start broad, then narrow** — create Spaces for major functions first; add Folders and Lists as work grows
2. **Keep statuses simple** — 3-5 statuses per workflow; use Custom Fields for sub-stages
3. **One source of truth per project** — don't duplicate tasks across Lists unnecessarily; use Relationships instead
4. **Template everything** — save Space, Folder, List, and Task templates for repeatable work
5. **Add views for different roles** — managers need Workload/Timeline; executors need List/Board
6. **Automate the routine** — status transitions, assignments, and notifications should be automated
7. **Use Docs for long-form content** — don't stuff everything into task descriptions
8. **Set up permissions early** — control who can see and edit each Space
9. **Train the team on hierarchy** — everyone must understand the Workspace -> Space -> Folder -> List -> Task chain
10. **Review and prune regularly** — archive old Lists, close stale tasks, consolidate unused Spaces

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Hurts | Fix |
|---|---|---|
| Too many Spaces | Navigation becomes unwieldy; people lose track of where work lives | Consolidate to 5-8 high-level Spaces |
| Tasks as Folders | Using tasks as project containers breaks views, reporting, and subtask limits | Folders hold projects; Lists hold workstreams; Tasks are work items |
| 15-20 custom statuses | Paralyzes the team with choices; "Everything View" becomes unreadable | Limit to 3-5 statuses; use Custom Fields for detail |
| No automations | Manual status changes, assignments, and notifications waste time | Automate at least status transitions and assignment routing |
| Duplicate tasks across Lists | Work gets out of sync; nobody knows which is the "real" task | Use Relationships or task-in-multiple-Lists feature |
| All work in one List | Impossible to filter, report, or manage permissions | Break into Folders and multiple Lists by workstream |
| No templates | Every project starts from scratch; inconsistent structure | Build templates for Spaces, Folders, Lists, and recurring tasks |

## Workspace Audit Checklist

Use this checklist to audit an existing ClickUp workspace:

- [ ] Are there fewer than 10 Spaces? If not, can some be merged?
- [ ] Does each Space have a clear owner?
- [ ] Do Folders group related Lists logically?
- [ ] Are status workflows consistent within each Space?
- [ ] Are Custom Fields serving a clear purpose, or are there unused fields?
- [ ] Are Automations documented and named clearly?
- [ ] Are templates available for repeatable work?
- [ ] Are Docs linked to their corresponding tasks/projects?
- [ ] Are permissions set correctly (who can see/edit each Space)?
- [ ] Is the Everything View usable, or is it cluttered with too many statuses?
- [ ] Are inactive Spaces, Folders, and Lists archived?
- [ ] Are time estimates used consistently for capacity planning?
