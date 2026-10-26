---
name: skillseal-bitrix24-crm
description: Use when configuring, auditing, or automating Bitrix24 CRM -- sales funnels, pipeline automation, leads/contacts, tasks, integrations, WhatsApp/telephony, reports, and troubleshooting.
version: 1.0.0
author: Workloop
license: MIT
---

# Bitrix24 CRM -- Operational Knowledge

## Overview

Bitrix24 is an all-in-one business platform combining CRM, task management, project management, communication tools (chat, video, telephony), website builder, HR, and BI (Business Intelligence). The CRM module is the centerpiece, designed to manage the full customer lifecycle from lead capture through post-sale retention.

The platform serves over 12 million organizations worldwide and is widely adopted by small and medium businesses in Brazil. It replaces the fragmented stack of Excel + WhatsApp + email + calendar with a unified, automatable system.

This skill covers real-world Bitrix24 CRM configuration, pipeline design, automation patterns, integrations, reporting, and troubleshooting. It draws from the full Bitrix24 Mastery ebook (37 chapters + bonus material) and field-tested deployment experience.

---

## Core CRM Entities

### Leads
- Unqualified contacts that enter via web forms, chat, email, phone, WhatsApp, Telegram, Instagram, Facebook Messenger, or manual entry.
- Store: name, contact info, source (UTM tags supported), comments, assigned responsible person.
- Lead sources: website, call, email, social media, advertisement, partner, recommendation, event, import.
- Status flow: New -> In Contact -> Qualified -> Converted.
- Convert to Contact + Company + Deal in a single action. The conversion preserves all lead data and activity history.
- Configurable duplicate detection rules.

### Contacts
- Qualified individuals with full profile: name, phones, emails, social profiles, address, custom fields.
- Belong to a Company (optional). One contact can link to multiple companies.
- Activity history fully tracked: calls, emails, meetings, tasks, deals, invoices, chat conversations.
- Built-in duplicate detection and merge wizard.
- Birthday and preference fields for relationship marketing.

### Companies
- Organizations with: name, industry, revenue, employee count, address, custom fields, type (client, partner, supplier, competitor, prospect).
- Contain Contacts and Deals. Company detail page shows full relationship graph with timeline.
- Can store: CNPJ/tax ID, website, multiple phone numbers, banking details.
- Company types drive segmentation in reports and automation rules.

### Deals
- Core pipeline entity. Represents a sales opportunity with value, stage, and probability.
- Links to Contact and Company. Multiple deals per contact/company supported.
- Fields: title, amount, currency, stage, probability, expected close date, assigned person, custom fields, source, comments.
- Products/line items can be added to track individual SKUs and auto-calculate totals.
- Categories: in-progress, won (success), lost (failure). Won/lost drives conversion analytics.

### Activities (Tasks, Calls, Meetings, Emails)
- Tasks: to-dos with deadline, priority (low/medium/high/critical), status, checklist subtasks, time tracking, dependencies.
- Calls: logged phone calls with duration, recording link, call notes, outcome.
- Meetings: scheduled with attendees, location, agenda, recurrence rules.
- Emails: sent/received within CRM, auto-attach to contact/deal timeline.
- All activities appear in the CRM timeline for each entity, forming a complete interaction audit trail.

### Products and Catalog
- Centralized product catalog: name, price, cost, category, image, SKU, unit of measure.
- Used in deals, quotes, and invoices. Supports inventory tracking (for applicable plans).
- Price types: base price, custom price per deal, discounts.
- Categories for organizing products by line, department, or service type.

### Quotes and Invoices
- Quotes (proposals): formal documents sent to contacts with products, prices, conditions, validity.
- Quote status: draft, sent, accepted, rejected.
- Invoices: bills generated from deals; track payment status and due dates.
- Integration with payment gateways available on Enterprise plans.

---

## Sales Funnels and Pipelines

### Pipeline Configuration
- Multiple pipelines supported (e.g., B2B Sales, B2C Sales, Service, Partner Channel, Recurring).
- Each pipeline has configurable stages: name, sort order, probability percentage, color, semantic (success/failure).
- Stages marked as "success" (won) or "failure" (lost) drive conversion and forecast reporting.
- Recommended: 4-7 stages per pipeline. Too few = lack of visibility; too many = maintenance burden.
- Pipelines can be scoped to specific CRM categories and user groups.

### Standard Pipeline Stages (example for service sales)
```
1. New Lead          -- 20%
2. Qualified         -- 40%
3. Demo / Meeting    -- 60%
4. Proposal Sent     -- 80%
5. Negotiation       -- 90%
6. Contract Signed   -- 100% (success)
7. Closed Lost       -- 0%   (failure)
```

### Multiple Pipelines Strategy
Use different pipelines for different sales motions:
- **B2B Sales**: longer cycle, more stages, higher values, approval gates.
- **B2C Sales**: short cycle, fewer stages, fast qualification.
- **Service/Consulting**: needs a "scoping" or "diagnosis" stage.
- **Recurring/Subscription**: includes "trial", "onboarding", "active".
- **Partner/Channel**: partner qualification, referral tracking.
- **Support Tickets**: triage, in-progress, resolved, closed (non-revenue funnel).

### Pipeline Automation Rules
- Stage-triggered automations: when deal enters stage X, execute task, notification, field update.
- Stage guards: mandatory fields required before advancing (e.g., "budget confirmed" before "Proposal Sent").
- SLA tracking: maximum time per stage with alerts on violation.
- Auto-assignment: route leads/deals by round-robin, territory, product type, or deal value.
- Auto-move: deal sitting too long in a stage can auto-advance or auto-escalate.

### Bottleneck Detection
- Identify stages where deals accumulate beyond normal time thresholds.
- Flag deals with no recent activity (stale deals at risk of going cold).
- Compare stage-to-stage conversion ratios over time.
- Detect abnormal concentration: 40%+ of pipeline in a single stage signals a bottleneck.
- Use `scripts/bitrix_audit.py` for automated pipeline analysis.

---

## Automation Engine (Business Processes)

### Triggers
- **CRM triggers**: lead created, lead converted, deal created, deal stage changed, deal won/lost, contact created/updated, company created/updated, invoice paid, activity completed.
- **Time triggers**: scheduled (daily, weekly, monthly), relative (X days after field date), absolute (specific date/time).
- **Manual triggers**: user clicks a button on an entity detail page.
- **External triggers**: incoming webhook, email received, chat message.

### Actions
- Create, update, or delete CRM entities.
- Send email or SMS via connected telephony provider.
- Internal notification (chat message, notification center, mobile push).
- Webhook/outgoing REST call to external URL with structured data payload.
- Execute custom PHP or JavaScript code (runs in Bitrix24 context with REST API access).
- Generate document from template (PDF invoice, contract, quote).
- Assign task to user, group, or department.
- Wait for condition (pause execution until a field changes or time elapses).
- Chain multiple actions with conditional branching (if/then/else).

### Automation Patterns (from field deployments)

**Lead Nurturing**:
```
Trigger: Lead created (source = website form)
  1. Assign to sales team (round-robin)
  2. Send welcome email (delay 1 hour)
  3. If no deal created in 3 days -> alert manager
  4. If contact responds -> create follow-up task
```

**Deal Follow-Up**:
```
Trigger: Deal enters "Proposal Sent"
  1. Log activity in timeline
  2. Create task: "Follow up on proposal" (due in 3 days)
  3. If deal still in same stage after 7 days -> alert sales manager
  4. If deal amount > $10,000 -> also alert director
```

**Post-Sale Onboarding**:
```
Trigger: Deal enters "Contract Signed" (won)
  1. Create onboarding project from template
  2. Assign tasks to delivery team
  3. Schedule satisfaction follow-up (30 days)
  4. Add contact to upsell campaign list
```

**Customer Retention Alert**:
```
Trigger: Contact submits complaint via support channel
  1. Tag contact as "At Risk"
  2. Assign to priority support queue
  3. Alert account manager
  4. Create retention task with 24-hour SLA
```

---

## Integrations

### WhatsApp
- Official Bitrix24 Connector via WhatsApp Business API (Open Channel).
- Receive messages in CRM chat; auto-create leads from new conversations.
- History stored in contact timeline: every message, image, document.
- Automated messages from business rules (Meta pre-approved templates required for outbound).
- Multi-agent routing with queues and round-robin distribution.
- Alternative: connect via third-party providers (Evolution API / Baileys) for non-official API scenarios.
- Quick replies, message templates, and away messages configurable.

### Telephony
- Built-in WebRTC softphone (no additional software needed).
- Providers: Twilio, Plivo, Voximplant, Asterisk (self-hosted PBX), and 30+ local telephony providers.
- Incoming call pop-up: recognizes caller by phone number, opens contact/deal card instantly.
- Call recording, transcription (AI-powered), call scoring.
- Missed-call auto-lead creation: every unanswered call becomes a lead.
- IVR (URA): interactive voice response menus for auto-routing.
- Extensions and internal calls between team members.

### Email
- Connect via IMAP/SMTP, Microsoft 365 (OAuth 2.0), or Gmail (OAuth 2.0).
- Send/receive within CRM; emails auto-attach to contact/deal timeline by address matching.
- Email templates with merge fields (contact name, deal value, assigned person, company name).
- Open tracking, click tracking, and link analytics.
- Shared mailboxes for team-wide visibility.
- Email-to-lead: forward an email to a Bitrix24 address to create a lead.

### Social Media
- Instagram: direct messages and comments in unified inbox.
- Facebook Messenger: messages appear alongside other channels.
- Telegram: chat integration with bot support.
- Viber, Skype, and additional channels via Open Channel framework.

### Website Widget
- Embeddable chat/contact widget via JavaScript snippet.
- Captures visitor name and contact info.
- Auto-creates leads with source tracking.
- Chat in real-time or offline message mode.
- Customizable greeting messages and appearance.

### Google Workspace and Microsoft 365
- Google Calendar: two-way sync, create/update events from CRM.
- Google Drive: attach files, create documents from templates.
- Google Meet: schedule and launch video meetings from deal/contact.
- Microsoft 365: similar integration for Outlook, OneDrive, Teams.

### REST API
- Full REST API at `https://yourdomain.bitrix24.com/rest/` with OAuth 2.0 authentication.
- Methods for all CRM entities: `crm.lead.*`, `crm.deal.*`, `crm.contact.*`, `crm.company.*`, `crm.activity.*`, `crm.product.*`, `crm.invoice.*`, `crm.quote.*`.
- Webhook events for real-time notifications: `ONCRMLEADADD`, `ONCRMDEALUPDATE`, `ONCRMCONTACTADD`, etc.
- Batch methods: execute multiple API calls in a single HTTP request.
- Rate limits: 2 req/s per method (self-hosted); cloud plans have burst limits that vary by tier.
- SDKs available for PHP, JavaScript, Python (community), and REST.

### Zapier, Make (Integromat), n8n
- Zapier: official Bitrix24 app with triggers and actions for most CRM events.
- Make: full module suite with deep CRM integration.
- n8n: community nodes available; also works via HTTP Request nodes calling REST API directly.
- Common automation: Bitrix24 deal won -> create invoice in accounting software -> notify finance team in Slack.

### Evolution API (WhatsApp via Baileys)
- Many Brazilian deployments use Evolution API as a WhatsApp bridge.
- Evolution connects a WhatsApp number to Bitrix24 via webhooks.
- Handles message sending, receiving, media, and status updates.
- n8n workflows bridge Evolution to Bitrix24 REST API for CRM logging.

---

## Reports and Analytics

### Standard CRM Reports
- **Sales Funnel**: conversion rate by stage, deal velocity (time from creation to close), pipeline value by stage.
- **Sales Performance by Employee**: closed deals, revenue, average deal size, conversion rate, activities count.
- **Lead Source Analysis**: channel performance by volume, conversion rate, deal value, ROI.
- **Deal Forecast**: weighted pipeline value using stage probabilities; projected revenue timeline.
- **Activity Report**: calls, emails, meetings by employee and date range.
- **Lost Deals Analysis**: reasons for loss, stage where deals are lost most often.
- **Invoice Report**: paid, overdue, outstanding by period and client.

### BI Builder (Advanced Analytics)
- Drag-and-drop report builder for custom dashboards.
- Dimensions: any CRM field, custom fields, date ranges, users, departments.
- Measures: count, sum, average, min, max, conversion rates.
- Visualization types: bar, line, pie, funnel, table, KPI gauges.
- Dashboards combine multiple widgets, filterable by date and responsible person.
- Export to Excel/CSV; schedule recurring email delivery (PDF or link).
- Row-level security: users see only their own data in reports.

### Key Pipeline Metrics to Track
- **Deal count by stage** (distribution health).
- **Weighted pipeline value** (sum of deal amount * stage probability / 100).
- **Average deal velocity** (days from creation to close).
- **Conversion rate per stage transition**.
- **Average days in stage** (identifies slow stages).
- **Win rate** (closed won / total closed).
- **Stale deals** (no activity in 14+ days).

---

## Common Configuration Patterns

### Setting Up a Sales Funnel
1. CRM -> Settings -> Pipelines.
2. Create new pipeline (name, category).
3. Define stages in order with names, win probabilities, and colors.
4. Mark final stages as "success" or "failure".
5. Configure stage guards: mandatory fields per stage.
6. Set up automation rules (robot) for each stage transition.
7. Assign pipeline to relevant user groups.

### Lead Capture Forms
1. CRM -> Settings -> CRM Forms.
2. Create form, select fields (name, phone, email, custom).
3. Configure: target pipeline, auto-assignment rules, auto-response email.
4. Enable UTM tracking for source attribution.
5. Embed via JavaScript snippet on website or share standalone URL.
6. Test with a sample submission to verify lead creation and assignment.

### Configuring WhatsApp via Open Channel
1. Contact Center -> WhatsApp.
2. Connect WhatsApp Business Account (requires Facebook Business verification).
3. Configure agent routing rules (round-robin, least busy, skill-based).
4. Set automated greetings and business hours.
5. Define away messages for outside hours.
6. Create automation rules: new WhatsApp conversation -> create lead -> assign -> notify.

### Configuring Telephony
1. Settings -> Telephony -> Connect provider.
2. Enter provider credentials (SIP, API key, etc.).
3. Configure phone numbers and extensions.
4. Set up IVR menu (welcome message, key options, routing).
5. Map phone number recognition to CRM lookup.
6. Enable call recording and transcription.

---

## Pipeline Health Monitoring

### Daily Review Checklist
1. Check deal distribution across stages (no stage should hold >40% of deals).
2. Identify deals with no activity in 7+ days (stale risk).
3. Review deals past expected close date.
4. Verify new leads are assigned within 1 hour.
5. Check automation execution logs for errors.
6. Look at stage-to-stage conversion trends (week-over-week).

### Red Flags
- 40%+ of deals concentrated in a single non-final stage.
- Average days in stage exceeds 2x the historical norm.
- Conversion rate drops sharply between two adjacent stages.
- Zero deals moved in a stage for 3+ days.
- Multiple deals past expected close date with no recent activity.

### Recovery Actions
- Stale deals: create follow-up task, re-engage customer, or move to lost after X days idle.
- Bottleneck stage: add capacity (more sales reps), automate handoff tasks, simplify stage requirements.
- Low conversion: review qualification criteria at the previous stage; are unqualified deals entering the pipeline?

---

## Troubleshooting

### Pipeline Health Issues
- Deals stuck in stage: check if mandatory fields are blocking advancement; review automation that should move them.
- Missing expected conversion: check if deals are being created in the wrong pipeline/stage; audit lead assignment rules.
- Inaccurate forecast: verify stage probabilities match actual historical win rates; adjust if >10% deviation.

### Automation Debugging
- Test all automation rules with a dedicated "Debug" pipeline before deploying to production.
- Use Automation Log (CRM -> Settings -> Automation -> Logs) to trace execution.
- Check automation triggers fire in correct order; sequential dependencies may break if ordering is wrong.
- Set up webhook error notifications: Bitrix24 can alert on failed external webhook calls.
- Common failure: field name mismatch between trigger condition and actual CRM field (case sensitivity).

### Integration Issues
- WhatsApp not connecting: verify Facebook Business verification status; check Open Channel configuration.
- Telephony: confirm provider credentials and that numbers are provisioned for the region.
- REST API: check OAuth token expiration; verify method name and required parameters match documentation.
- Email: IMAP/SMTP ports may be blocked; test connectivity from the Bitrix24 server.

### Performance
- Archive old leads and deals for datasets exceeding 100,000 entities.
- Limit custom fields to reduce query overhead; every custom field slows list views.
- Schedule heavy reports during off-hours to avoid impacting CRM responsiveness.
- Use batch API methods instead of sequential single-record calls.

---

## Scripts

### Pipeline Audit (`scripts/bitrix_audit.py`)

Analyzes a Bitrix24 pipeline dataset and generates a comprehensive health report.

**Usage:**
```bash
python3 scripts/bitrix_audit.py '{"pipeline_name":"Sales","stages":[...],"deals":[...]}'
python3 scripts/bitrix_audit.py path/to/pipeline_data.json
python3 scripts/bitrix_audit.py data.json --stale-days 10 --bottleneck-days 25 --json
```

**Options:**
- `--stale-days N`: max days without activity before flagging stale (default: 14).
- `--bottleneck-days N`: max average days in stage before flagging bottleneck (default: 30).
- `--bottleneck-pct N`: max percentage of deals in one stage before flagging (default: 40).
- `--json`: also output raw JSON results.

**Input JSON schema:**
```json
{
  "pipeline_name": "Sales Pipeline",
  "stages": [
    {"name": "New Lead", "order": 1, "probability": 20},
    {"name": "Qualified", "order": 2, "probability": 40},
    {"name": "Proposal Sent", "order": 3, "probability": 60},
    {"name": "Negotiation", "order": 4, "probability": 80},
    {"name": "Closed Won", "order": 5, "probability": 100},
    {"name": "Closed Lost", "order": 6, "probability": 0}
  ],
  "deals": [
    {
      "id": "DL-001",
      "title": "Acme Corp Software License",
      "stage": "Proposal Sent",
      "amount": 15000.00,
      "entered_stage_date": "2025-06-10",
      "last_activity_date": "2025-06-15",
      "assigned_to": "John Silva"
    }
  ]
}
```

**Output sections:**
1. **Header**: pipeline name, analysis date, total deals, total pipeline value, weighted value.
2. **Stage Metrics table**: count, percentage, average days, total amount per stage.
3. **Conversion Rates**: transition counts and rates between consecutive stages.
4. **Bottlenecks**: time-based (avg days > threshold) and concentration-based (>pct threshold).
5. **Stale Deals**: list of deals with no activity beyond the stale threshold.

---

## Reference: Bitrix24 Mastery Ebook

This skill's knowledge base draws from "Bitrix24 Mastery: Do Zero ao Especialista" (37 chapters + bonus), covering:

- Chapters 1-3: Platform overview, plans, installation.
- Chapters 4-6: Company setup, users, permissions, branding, custom fields, security.
- Chapters 7-9: Full CRM module (leads, contacts, companies, deals, quotes, products), sales funnels, custom fields.
- Chapter 10: CRM automation (robots, triggers, rules, approvals, alerts).
- Chapters 11-13: Contact Center, Open Channels, telephony.
- Chapters 14-17: Tasks, projects, Scrum, Kanban, Gantt, workgroups.
- Chapters 18-21: Drive, documents, HR, knowledge base.
- Chapters 22-25: Business processes, workflows, RPA, AI features.
- Chapters 26-30: Integrations (WhatsApp, Google, Microsoft, APIs, webhooks, n8n).
- Chapters 31-34: BI, dashboards, reports, administration, security, backups.
- Chapters 35-37: Troubleshooting (150+ common problems), consulting methodology, real-world cases (11 segments).
- Bonus: Implementation checklist, templates, and advanced automation recipes.
