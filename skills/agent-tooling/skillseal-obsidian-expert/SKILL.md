---
name: skillseal-obsidian-expert
description: "Obsidian second brain expert: vault architecture, atomic notes, bidirectional links, MOCs, Zettelkasten method, Dataview queries, plugin selection, and knowledge graph optimization. Covers real-world workflows and best practices for building a durable personal knowledge management system."
version: 1.0.0
author: Workloop
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [obsidian, second-brain, zettelkasten, knowledge-management, markdown, vault, dataview, plugins, notes, pkm]
    category: productivity
    related_skills: [rag-engineering, obsidian-mastery-referencia]
---

# Obsidian Expert -- Second Brain Architecture and Knowledge Management

Comprehensive guidance for building and maintaining a high-quality Obsidian vault as a second brain. Covers vault design, atomic notes, bidirectional linking, Maps of Content (MOCs), the Zettelkasten method, Dataview queries, plugin selection, and vault health auditing.

## When to Use This Skill

Use this skill when the task involves:

- Designing or restructuring an Obsidian vault for long-term knowledge management
- Creating atomic notes with proper linking, tagging, and metadata conventions
- Building Maps of Content (MOCs) to navigate large knowledge bases
- Applying the Zettelkasten method (fleeting notes, literature notes, permanent notes)
- Writing Dataview queries to surface insights from structured metadata
- Selecting and configuring core plugins (Dataview, Templater, Tasks, Calendar, Excalidraw)
- Auditing a vault for structural problems: orphan notes, missing links, tag sprawl, inconsistent frontmatter
- Integrating Obsidian with RAG systems or AI assistants

Do NOT use this skill for: general markdown editing, unrelated note-taking apps (Notion, Roam, Logseq), or Obsidian Sync troubleshooting.

## Core Concepts

### The Vault

A vault is a folder of plain-text Markdown files on your local filesystem. Obsidian reads and writes `.md` files directly -- there is no proprietary database. This design gives you:

- **Full data ownership**: your notes are plain files you control
- **Portability**: open the same vault with any text editor
- **Git-friendly**: version control works naturally with markdown files
- **Future-proof**: no vendor lock-in, no export needed

Recommended vault structure:

```
vault/
  _attachments/         # Images, PDFs, audio files
  _templates/           # Note templates (used by Templater or core Templates)
  _scripts/             # Dataview or Templater JS scripts
  0-inbox/              # Capture zone -- unprocessed incoming notes
  1-fleeting/           # Quick thoughts, daily notes
  2-literature/         # Source-based notes (articles, books, videos)
  3-permanent/          # Evergreen / permanent notes (your own ideas)
  4-mocs/               # Maps of Content (navigation hubs)
  5-projects/           # Active projects with deadlines
  6-archive/            # Completed or dormant material
  +daily/               # Daily notes (if not using Periodic Notes plugin)
```

Key vault-level configuration files (`.obsidian/`):

- `app.json` -- editor and appearance settings
- `appearance.json` -- theme and CSS snippets
- `core-plugins.json` -- which core plugins are enabled
- `community-plugins.json` -- which community plugins are enabled
- `hotkeys.json` -- custom keyboard shortcuts
- `templates.json` -- core Templates plugin settings
- `workspace.json` -- last workspace layout

### Atomic Notes

An atomic note captures exactly one idea, concept, or fact. It is:

- **Self-contained**: can be understood without reading other notes
- **Single-concept**: one idea per note, not a dump of related thoughts
- **Densely linked**: connects to other atomic notes via `[[wikilinks]]`
- **Properly titled**: the title is a full statement or precise concept name (not "Notes on X" or "Chapter 3")

Example of a good atomic note title: `Synaptic pruning increases neural efficiency during adolescence`
Example of a poor title: `Brain stuff`

Anatomy of a well-formed atomic note:

```markdown
---
created: 2025-03-15
tags:
  - neuroscience
  - learning
aliases:
  - neural pruning
related:
  - "[[myelination]]"
  - "[[critical periods]]"
source:
  - "[[Doidge 2007 - The Brain That Changes Itself]]"
---

# Synaptic pruning increases neural efficiency during adolescence

During adolescence, the brain eliminates roughly 50% of synaptic connections
created during childhood. This process, called synaptic pruning, follows a
"use it or lose it" principle -- frequently used connections are strengthened
while unused ones are removed.

Pruning is essential for:

- **Cognitive efficiency**: fewer but stronger pathways reduce metabolic cost
- **Specialization**: neural circuits become tuned to the individual's
  environment
- **Critical periods**: pruning windows explain why some skills (language,
  music) are harder to acquire after adolescence

See also: [[myelination]] which wraps surviving axons in insulating myelin,
further speeding signal transmission.

## References

- Doidge, N. (2007). The Brain That Changes Itself. Penguin.
- Huttenlocher, P. R. (1979). Synaptic density in human frontal cortex.
  Brain Research, 163(2), 195-205.
```

### Bidirectional Links

Obsidian's core differentiator is bidirectional linking via `[[wikilinks]]`. When Note A links to Note B, Obsidian automatically shows the connection in both directions:

- **Outgoing links**: links FROM the current note (visible in the right sidebar)
- **Backlinks**: links TO the current note from other notes (visible in the backlinks panel)
- **Unlinked mentions**: references to the note's title that are not yet linked (opportunities to create new connections)

Linking conventions:

1. **Link generously**: when a concept appears, link it. Dense links make the graph useful.
2. **Use aliases**: `[[Doidge 2007 - The Brain That Changes Itself|Doidge (2007)]]` for readability.
3. **Prefer direct links over folder hierarchy**: folders organize for storage; links organize for discovery.
4. **Link to MOCs from related notes**: `## Related` sections should point to the relevant MOC.

### Tags vs Links

| Feature | Tags (`#tag`) | Links (`[[note]]`) |
|---|---|---|
| Granularity | Coarse -- categories/statuses | Fine -- specific concepts |
| Use case | `#draft`, `#neuroscience`, `#todo` | `[[synaptic pruning]]`, `[[Doidge 2007]]` |
| Hierarchy | Nested: `#topic/subtopic` | Flat (but can group via MOCs) |
| Queryable | Yes (Dataview, search) | Yes (backlinks, Dataview `FROM`) |
| Best practice | Use sparingly (3-7 tags per note) | Use generously (many links per note) |

Tag conventions:

- **Type tags**: `#permanent`, `#literature`, `#fleeting`, `#moc`, `#daily`
- **Status tags**: `#draft`, `#review`, `#published`, `#archived`
- **Domain tags**: `#neuroscience`, `#programming`, `#design`
- **Action tags**: `#todo`, `#todo/now`, `#todo/later`

Avoid tag sprawl: every new tag should serve a clear query or filtering purpose.

### Maps of Content (MOCs)

A Map of Content is a curated navigation note that links to related atomic notes and provides structure. Think of it as a table of contents that grows organically -- not a rigid hierarchy, but a flexible entry point.

MOC conventions:

1. **Name pattern**: `MOC Neuroscience`, `MOC Programming Languages`, `MOC Project Alpha`
2. **Tag with `#moc`** for easy filtering
3. **Include a brief description** of the domain
4. **Group links under descriptive headings**
5. **Link back to the MOC** from every note it references (bidirectional)

Example MOC:

```markdown
---
tags: [moc, neuroscience]
created: 2025-01-10
---

# MOC Neuroscience

Entry point for all neuroscience notes. Covers brain structure, development,
learning, and disorders.

## Core Concepts

- [[synaptic pruning]] -- elimination of unused connections
- [[myelination]] -- insulating axons for faster transmission
- [[neuroplasticity]] -- the brain's ability to reorganize
- [[long-term potentiation]] -- cellular basis of learning

## Development

- [[critical periods]] -- windows of heightened plasticity
- [[adolescent brain development]] -- prefrontal cortex maturation
- [[brain-derived neurotrophic factor]] -- BDNF and learning

## Key Sources

- [[Doidge 2007 - The Brain That Changes Itself]]
- [[Kandel 2012 - Principles of Neural Science]]
```

### Zettelkasten Method

The Zettelkasten (German for "slip box") is the intellectual ancestor of atomic notes, developed by sociologist Niklas Luhmann. He produced over 90,000 handwritten index cards, organized not by topic hierarchy but by a branching sequence of links.

The three types of notes in Zettelkasten:

1. **Fleeting notes** (`1-fleeting/`): quick captures -- ideas, reminders, observations. Process within 24-48 hours or discard them. These are raw and unpolished.

2. **Literature notes** (`2-literature/`): your summary of a source in your own words. One note per source (book, article, video). Include bibliographic metadata and key claims. Always link back to the source reference.

3. **Permanent notes** (`3-permanent/`): one atomic idea per note, written as if for publication. Full sentences, clear arguments, dense links to other permanent notes. These are the durable output of your thinking.

The workflow:

```
Capture (fleeting) --> Process (literature) --> Develop (permanent) --> Connect (MOCs + links)
```

Key Zettelkasten principles:

- **Atomicity**: one idea per note. If a note has two ideas, split it.
- **Autonomy**: every permanent note should be understandable on its own.
- **Connection**: always link a new permanent note to existing ones. Luhmann asked: "In which context will I stumble upon this note again?"
- **Own words**: never copy-paste. Rewriting forces understanding.
- **Surprise**: the value of a Zettelkasten emerges from unexpected connections between notes, not from retrieval of known ones.

### Dataview

Dataview is the most powerful community plugin for Obsidian. It treats your vault as a queryable database, indexing metadata from YAML frontmatter and inline fields.

#### Basic Queries

List all permanent notes:
```dataview
LIST
FROM #permanent
SORT file.ctime DESC
```

Table of literature notes with source authors:
```dataview
TABLE author, year, tags
FROM #literature
SORT year DESC
```

Tasks across the vault:
```dataview
TASK
FROM "5-projects"
WHERE !completed
GROUP BY file.link
```

#### Advanced Patterns

Notes with no outgoing links (orphans):
```dataview
LIST
FROM ""
WHERE length(file.outlinks) = 0
AND file.name != "Home"
SORT file.name ASC
```

Recently modified permanent notes:
```dataview
TABLE file.mtime AS "Last Modified", tags
FROM #permanent
WHERE file.mtime >= date(today) - dur(7 days)
SORT file.mtime DESC
```

Notes linked to a specific concept:
```dataview
LIST
FROM [[synaptic pruning]]
```

Dataview field conventions for frontmatter:

| Field | Type | Purpose |
|---|---|---|
| `created` | date | When the note was first created |
| `modified` | date | Last modification (auto if using Templater) |
| `tags` | list | YAML list: `[tag1, tag2]` |
| `aliases` | list | Alternative titles for linking |
| `related` | list | Wikilinks to related notes |
| `source` | list | Wikilinks to source/literature notes |
| `status` | string | `draft`, `review`, `published`, `archived` |
| `author` | string | Author name (for literature notes) |
| `year` | number | Publication year (for literature notes) |

#### DataviewJS

For complex logic, DataviewJS provides full JavaScript access:

```dataviewjs
const pages = dv.pages('#permanent')
  .where(p => p.file.outlinks.length === 0)
  .sort(p => p.file.name);

dv.list(pages.map(p => p.file.link));
```

### Essential Plugins

#### Core Plugins (built-in, enable selectively)

- **Backlinks**: show notes that link to the current note (enable always)
- **Outgoing Links**: show notes the current note links to (enable always)
- **Graph View**: visual map of note connections (enable for navigation)
- **Templates**: insert reusable note skeletons (enable always)
- **Daily Notes**: one note per day (enable if you do daily journaling)
- **Canvas**: infinite canvas for visual thinking (enable if needed)
- **Command Palette**: quick actions via Ctrl/Cmd+P (enable always)
- **Quick Switcher**: jump to any note by name (enable always)

#### Community Plugins (install as needed, not all at once)

**Tier 1 -- Install immediately:**

- **Dataview**: query your vault as a database. Prerequisite for any serious vault.
- **Templater**: advanced templates with JavaScript, date math, file creation triggers. Replaces core Templates.
- **Calendar**: visual calendar that creates/opens daily notes. Works with Daily Notes or Periodic Notes.

**Tier 2 -- Add when you hit the need:**

- **Tasks**: task management with due dates, priorities, recurring tasks, and queries.
- **Excalidraw**: embed hand-drawn diagrams and sketches directly in notes.
- **Kanban**: drag-and-drop boards for project management.
- **Periodic Notes**: daily, weekly, monthly, quarterly notes on a schedule.
- **Quick Add**: capture ideas instantly from anywhere with a hotkey.
- **Omnisearch**: fuzzy search across vault content (better than built-in search for large vaults).
- **Tag Wrangler**: rename tags across the entire vault in one operation.
- **Note Refactor**: split a long note into atomic notes (extract selection to new note).

**Tier 3 -- Power users:**

- **Breadcrumbs**: hierarchical relationships between notes (parent/child/sibling).
- **Metadata Menu**: GUI for editing frontmatter, with field types and autocomplete.
- **DB Folder**: Notion-like database views inside Obsidian.
- **Make.md**: custom workspaces, spaces, and flow-based organization.
- **Obsidian Git**: auto-commit and push vault to GitHub on a schedule.

Plugin hygiene: fewer plugins means fewer points of failure and faster startup. Uninstall plugins you are not actively using.

## Vault Health Audit

A healthy vault is one where notes are well-connected, tagged consistently, and free of structural problems. Run audits periodically.

### Health Metrics

| Metric | Healthy Target | Red Flag |
|---|---|---|
| Orphan notes (no links in/out) | Under 5% of total | Over 15% -- notes are disconnected |
| Average links per note | 3-10 | Under 1 -- insufficient connection |
| Tag count (unique tags) | 20-50 for medium vaults | Over 100 -- tag sprawl |
| Notes per tag | 5-200 | Under 3 -- tag is too narrow; over 500 -- tag is too broad |
| MOC coverage | 80%+ of permanent notes linked from at least one MOC | Under 50% -- content is hard to discover |
| Frontmatter completeness | 90%+ of notes have `created` and `tags` | Under 60% -- Dataview queries cannot surface notes |
| Stale notes (no edits in 6+ months) | Under 30% | Over 60% -- vault is accumulating cruft |

### Common Problems and Fixes

**Orphan notes** -- Notes with zero incoming and zero outgoing links.
- Fix: Review each orphan. Link it to related notes or MOCs, or archive/delete it if it is no longer relevant.

**Tag sprawl** -- Too many unique tags, many used only once.
- Fix: Consolidate similar tags (e.g., `#psychology`, `#psych`, `#psychologie` -> `#psychology`). Use Tag Wrangler plugin for bulk renames.

**Stub notes** -- Notes with only a title and no body content.
- Fix: Either fill them in or delete them. Empty notes add noise to search and graph.

**Dead links** -- Wikilinks pointing to notes that do not exist.
- Fix: Create the missing note if the concept is important, or remove the link.

**Flat structure** -- All notes in a single folder with no organization.
- Fix: This is actually fine for a Zettelkasten. Folders are for storage, not for discovery. But if you need folder organization, use a PARA-inspired structure.

**Over-nesting** -- Deep folder hierarchies (4+ levels).
- Fix: Flatten to 2-3 levels maximum. Deep nesting hides notes and discourages linking.

**Inconsistent frontmatter** -- Different field names for the same concept across notes.
- Fix: Standardize field names. Use Templater to enforce consistent frontmatter on note creation.

### The Audit Script

This skill includes `scripts/obsidian_audit.py` for automated vault health checks:

```bash
python3 obsidian_audit.py /path/to/vault
```

The script analyzes folder structure, link density, orphan notes, tag usage, and frontmatter completeness. It produces a graded report with actionable recommendations.

## Integration with AI and RAG

Obsidian vaults are excellent knowledge bases for Retrieval-Augmented Generation (RAG):

1. **All content is in plain text** (`.md` files) -- easy to chunk and embed
2. **Frontmatter provides structured metadata** for filtering and routing
3. **Wikilinks reveal semantic relationships** that improve retrieval
4. **MOCs serve as natural summaries** for domain-specific queries

See the `rag-engineering` skill for implementation patterns.

## Vault Design Principles

1. **Flat is better than nested**: use links for structure, not folders
2. **Atomic is better than encyclopedic**: one idea per note
3. **Linked is better than isolated**: every note should have at least one connection
4. **Written in your own words**: understanding over transcription
5. **Immediately useful**: capture only what you will actually reference later
6. **Iterative over planned**: start messy, refine as connections emerge
7. **Files over database**: plain text ensures durability

## Common Pitfalls

- **Collection over connection**: hoarding notes without linking them. The value is in the connections, not the volume.
- **Premature organization**: spending hours on folder structures before writing notes. Let structure emerge from content.
- **Plugin overload**: installing 50 plugins on day one. Start with Dataview and Templater only.
- **Perfect note syndrome**: waiting until a note is "perfect" before publishing it. Notes are never finished -- they evolve.
- **Daily Notes as dumping ground**: using daily notes to capture everything without processing. Daily notes are an inbox, not a destination.
- **Ignoring backlinks**: never checking what links to a note. Backlinks reveal unexpected connections.
- **No review workflow**: writing notes and never revisiting them. Schedule regular reviews to refine and connect.

*Knowledge based on the Zettelkasten method (Luhmann), Building a Second Brain (Forte), and the Obsidian Mastery ebook (Workloop).*
