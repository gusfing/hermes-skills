---
name: skillseal-n8n-automation
description: Design, build, debug, and optimise n8n workflow automations. Covers nodes, webhooks, expressions, error handling, parallel execution, integrations, and workflow diagnostics.
version: 1.0.0
author: Workloop
license: MIT
---

# n8n Automation

Comprehensive guidance for building production-grade workflow automations in n8n. This skill covers workflow architecture, node configuration, expression language, error handling patterns, parallel execution strategies, and systematic diagnostics for broken or underperforming workflows.

## Table of Contents

1. [Workflow Fundamentals](#workflow-fundamentals)
2. [Node Reference](#node-reference)
3. [Webhook Triggers](#webhook-triggers)
4. [n8n Expression Language](#n8n-expression-language)
5. [Conditional Logic: IF and Switch](#conditional-logic-if-and-switch)
6. [Error Handling](#error-handling)
7. [Parallel Execution](#parallel-execution)
8. [Integrations and Credentials](#integrations-and-credentials)
9. [Best Practices](#best-practices)
10. [Workflow Diagnostics](#workflow-diagnostics)

---

## Workflow Fundamentals

### Structure of an n8n Workflow JSON

An n8n workflow is a JSON object with five top-level keys:

```json
{
  "name": "My Workflow",
  "nodes": [],
  "connections": {},
  "settings": {},
  "staticData": null,
  "pinData": {}
}
```

- **name** (string): Human-readable workflow name.
- **nodes** (array): Every step in the workflow. Each node has a `type`, `name`, `position`, and `parameters`.
- **connections** (object): Directed edges between nodes. Keys are source node names; values map output indices to arrays of `{ node, type, index }` target descriptors.
- **settings** (object): Workflow-level configuration (timezone, error workflow binding, execution order, caller IDs).
- **staticData** (object): Persistent key-value store scoped to a workflow instance (survives execution restarts).
- **pinData** (object): Pinned (mock) output data per node, used to test downstream nodes without real execution.

### Execution Model

n8n executes workflows node-by-node. Each node receives data items from its upstream parent and processes them through the node's operation. The output is an array of items passed to downstream nodes. A node can produce zero, one, or many output items per input item.

Execution flows from triggers (nodes with type ending in `Trigger`) through the connection graph. When multiple nodes feed into one node, the target node receives all upstream data items merged into a single array.

### Execution Order Settings

Under `settings.executionOrder`:

- **`v0` (legacy)**: Executes nodes based on graph position; less deterministic.
- **`v1` (recommended)**: Executes nodes based on input order; deterministic and predictable. This is the default in n8n 1.0+.

---

## Node Reference

### Core Nodes

| Node Type | Purpose | Key Parameters |
|-----------|---------|---------------|
| `n8n-nodes-base.manualTrigger` | Manual execution trigger | None (fires on manual run) |
| `n8n-nodes-base.webhook` | Incoming HTTP webhook | `httpMethod`, `path`, `responseMode`, `options` |
| `n8n-nodes-base.httpRequest` | Outbound HTTP calls | `method`, `url`, `authentication`, `sendHeaders`, `sendBody`, `options` |
| `n8n-nodes-base.if` | Conditional branching | `conditions` array with `value1`, `operation`, `value2` |
| `n8n-nodes-base.switch` | Multi-path routing | `dataPropertyName`, `rules` array, `fallbackOutput` |
| `n8n-nodes-base.set` | Set/transform data fields | `values` — key-value pair assignments (supports expressions) |
| `n8n-nodes-base.function` | Custom JavaScript | `code` — full Node.js sandbox with lodash and Luxon |
| `n8n-nodes-base.functionItem` | Per-item JavaScript | `code` — runs once per input item |
| `n8n-nodes-base.code` | Python or JS execution | `mode` (runOnceForAllItems or runOnceForEachItem), `language`, `code` |
| `n8n-nodes-base.splitInBatches` | Batch processing | `batchSize`, `options` |
| `n8n-nodes-base.merge` | Merge two data streams | `mode` (append, combine, etc.), `mergeByFields` |
| `n8n-nodes-base.limit` | Cap item count | `maxItems` |
| `n8n-nodes-base.wait` | Pause execution | `resume`, `unit`, `amount` |
| `n8n-nodes-base.errorTrigger` | Catch upstream errors | None (receives error data from error workflow binding) |
| `n8n-nodes-base.executeWorkflow` | Call sub-workflow | `source` (local or URL), `workflowId` |
| `n8n-nodes-base.noOp` | Pass-through (no-op) | None; used as routing placeholder |

### Trigger Nodes

| Node Type | Trigger Method |
|-----------|---------------|
| `n8n-nodes-base.webhookTrigger` | HTTP webhook |
| `n8n-nodes-base.scheduleTrigger` | Cron / interval timer |
| `n8n-nodes-base.telegramTrigger` | Telegram bot messages |
| `n8n-nodes-base.emailTrigger` (IMAP) | Incoming email |
| `n8n-nodes-base.rabbitmqTrigger` | RabbitMQ queue messages |
| `n8n-nodes-base.redisTrigger` | Redis pub/sub channels |
| `n8n-nodes-base.googleSheetsTrigger` | Google Sheets row changes |

---

## Webhook Triggers

### Webhook Node Configuration

```json
{
  "type": "n8n-nodes-base.webhook",
  "name": "Incoming Webhook",
  "parameters": {
    "httpMethod": "POST",
    "path": "my-webhook-endpoint",
    "responseMode": "onReceived",
    "options": {
      "responseCode": 200,
      "responseData": "firstEntryJson",
      "responseHeaders": {},
      "propertyName": "data",
      "rawBody": false
    }
  }
}
```

### Response Modes

- **`onReceived`**: Responds immediately when the webhook receives data. Downstream nodes execute in the background after the HTTP response is sent. Best for fire-and-forget scenarios and avoiding timeouts.
- **`lastNode`**: Executes the full workflow synchronously and returns the last node's output as the webhook response. Use when the caller needs the result.
- **`responseNode`**: Like `lastNode` but you designate a specific "Respond to Webhook" node to control exactly what gets returned.
- **`redirect`**: Returns an HTTP redirect (30x) to the caller.

### Webhook Authentication

Configure under `options.authentication`:

- **Basic Auth**: Provide username and password; n8n checks `Authorization` header.
- **Header Auth**: Specify a header name and expected value.
- **None**: Open (only recommended for internal/test workflows behind a firewall).

### Production Webhook URL Pattern

```
https://<n8n-instance>/webhook/<webhook-path>
```

Or when using the test webhook:
```
https://<n8n-instance>/webhook-test/<webhook-path>
```

Production webhooks are activated when the workflow is set to "Active". Test webhooks work even when inactive (for development).

---

## n8n Expression Language

### Syntax

Expressions are enclosed in double curly braces: `{{ expression }}`. They are evaluated at runtime against the current execution context.

### Accessing Data

```
{{ $json.field_name }}              -- Current item's JSON field
{{ $json["field-name"] }}           -- Bracket notation for special chars
{{ $binary.fileName }}              -- Binary data properties
{{ $node["Node Name"].json.field }} -- Access output from a named node
{{ $itemIndex }}                    -- Zero-based index of the current item
{{ $now }}                          -- Current DateTime (Luxon)
{{ $today }}                        -- Current date at midnight
{{ $runIndex }}                     -- Execution run index
{{ $workflow.name }}                -- Workflow name
{{ $workflow.id }}                  -- Workflow ID
{{ $execution.id }}                 -- Current execution ID
{{ $execution.resumeUrl }}          -- URL to resume a Wait node
{{ $prevNode.name }}                -- Name of the immediate upstream node
{{ $parameter }}                    -- Current node's own parameter values
```

### JSON and Array Operations

```
{{ $json.field.filter(x => x.active) }}         -- Filter array
{{ $json.items.map(x => x.id) }}                -- Map/extract field
{{ $json.orders.reduce((sum, o) => sum + o.total, 0) }} -- Reduce
{{ $json.list.slice(0, 10) }}                   -- Slice first N items
{{ $json.obj.hasOwnProperty("key") }}           -- Check key existence
{{ Object.keys($json) }}                        -- Get all keys
{{ JSON.stringify($json) }}                     -- Serialize to string
```

### String Manipulation

```
{{ $json.name.toUpperCase() }}
{{ $json.email.trim() }}
{{ $json.text.includes("urgent") }}
{{ $json.url.startsWith("https://") }}
{{ "Hello " + $json.firstName }}
{{ `Value is ${$json.count}` }}                 -- Template literal
{{ $json.slug.replace(/\s+/g, "-") }}           -- Regex replace
```

### Date and Time (Luxon)

```
{{ $now.plus({ days: 7 }).toISO() }}
{{ $now.toFormat("yyyy-MM-dd HH:mm:ss") }}
{{ $now.setZone("America/Sao_Paulo").toISO() }}
{{ DateTime.fromISO($json.timestamp).toRelativeCalendar() }}
{{ $today.diff(DateTime.fromISO($json.birthDate), "years").years }}
```

### Math and Utility

```
{{ Math.round($json.price * 1.1 * 100) / 100 }}
{{ Math.max(...$json.values) }}
{{ $json.count || 0 }}                          -- Fallback to 0 if falsy
{{ $json.name ?? "Unnamed" }}                   -- Nullish coalescing
{{ _.uniq($json.tags) }}                        -- Lodash (available globally)
{{ _.groupBy($json.items, "category") }}
```

### Edge Cases

- Expressions inside strings: `"User ID: {{ $json.id }}"` — the whole string becomes the expression result.
- Numeric fields with expressions: wrap in `{{ }}` only if the entire value is the expression.
- If an expression evaluates to `undefined`, n8n skips the item (unless configured otherwise).

---

## Conditional Logic: IF and Switch

### IF Node

Routes data to one of two outputs (true/false) based on conditions.

```json
{
  "type": "n8n-nodes-base.if",
  "name": "Check Status",
  "parameters": {
    "conditions": {
      "options": {
        "combinator": "and"
      },
      "conditions": [
        {
          "id": "cond-1",
          "leftValue": "={{ $json.status }}",
          "rightValue": "active",
          "operator": {
            "type": "string",
            "operation": "equals"
          }
        },
        {
          "id": "cond-2",
          "leftValue": "={{ $json.priority }}",
          "rightValue": 1,
          "operator": {
            "type": "number",
            "operation": "greaterEqual"
          }
        }
      ]
    }
  }
}
```

**Combinators**: `and` (all conditions must pass) or `or` (any condition passes).

**Operator types**: `string`, `number`, `dateTime`, `boolean`, `array`, `object`, `exists`/`notExists`.

**Key operators per type**:
- **string**: `equals`, `notEquals`, `contains`, `notContains`, `startsWith`, `endsWith`, `regex`, `isEmpty`, `isNotEmpty`
- **number**: `smaller`, `smallerEqual`, `larger`, `largerEqual`, `equals`, `notEquals`
- **exists**: `exists`, `notExists` (checks if field is defined, not null, not empty string)

### SWITCH Node

Routes data to one of N outputs based on matching rules. Unlike IF (binary), Switch handles many discrete conditions efficiently.

```json
{
  "type": "n8n-nodes-base.switch",
  "name": "Route by Type",
  "parameters": {
    "dataPropertyName": "type",
    "rules": {
      "rules": [
        { "value": "order", "output": 0 },
        { "value": "refund", "output": 1 },
        { "value": "inquiry", "output": 2 }
      ]
    },
    "options": {
      "fallbackOutput": "extra"
    }
  }
}
```

- **`dataPropertyName`**: The JSON field to compare against rules.
- **`rules`**: Array of `{ value, output }` mappings. `output` is the 0-based output index.
- **`fallbackOutput`**: Route unmatched items to `extra` output (enabled via options) or `none` (drop them). When set to `none`, unmatched items are discarded.

### When to Use IF vs Switch

| Scenario | Recommendation |
|----------|---------------|
| Binary yes/no decision | IF node |
| 3-7 discrete values, simple matching | Switch node |
| Complex multi-rule logic with AND/OR | IF node with multiple conditions |
| Value falls into one of many buckets | Switch node |
| Need regex or range comparisons | IF node |

---

## Error Handling

### Error Workflow Pattern

n8n supports a dedicated error workflow that triggers automatically when any execution in the main workflow fails.

1. **Bind an error workflow** in the main workflow's settings:
   ```json
   "settings": {
     "errorWorkflow": "Error Handler Workflow Name or ID",
     "callerPolicy": "workflowsFromSameOwner"
   }
   ```

2. **In the error workflow**, use the `n8n-nodes-base.errorTrigger` node as the trigger. It receives the error payload with:
   - `error.message`: Error description
   - `error.node`: Name of the failed node
   - `error.stack`: Stack trace
   - `execution.id`: The failed execution ID
   - `workflow.id`: The main workflow's ID
   - `workflow.name`: The main workflow's name
   - `itemIndex`: The item being processed when it failed

### Try/Catch with Error Trigger (Intermediate Node)

For granular control, place an Error Trigger node as a regular downstream node connected to both the success and error outputs:

1. Connect the risky node's main output to your happy path.
2. Connect a second Error Trigger node that references the risky node.
3. The Error Trigger catches failures from its parent and routes them to a fallback path within the same workflow.

### Error Output on HTTP Request

The HTTP Request node has an "Error" output (enabled via `options.allowUnauthorizedCerts` and `options.neverError`):

```json
{
  "type": "n8n-nodes-base.httpRequest",
  "name": "API Call",
  "parameters": { ... },
  "onError": "continueRegularOutput"
}
```

When `onError` is `continueRegularOutput`, errors appear as items with `__error` metadata. When `continueErrorOutput`, errors route to a separate "Error" output connector.

### Retry Logic

n8n does not have a native retry node, but you can implement retries:

1. **Wait + Loop**: Use a Wait node with a fixed interval, then loop back to the HTTP Request. Track attempts in `staticData` or pass a counter field.
2. **Code Node**: Write a retry loop inside a Function or Code node with exponential backoff:
   ```javascript
   const maxRetries = 3;
   let attempt = 0;
   let result;
   while (attempt < maxRetries) {
     try {
       result = await this.helpers.httpRequest({ url, method: 'GET' });
       break;
     } catch (e) {
       attempt++;
       if (attempt >= maxRetries) throw e;
       await new Promise(r => setTimeout(r, 1000 * Math.pow(2, attempt)));
     }
   }
   return result;
   ```

### Common Error Patterns and Fixes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Cannot read properties of undefined` | Missing field in input data | Use `{{ $json.field ?? "default" }}` or `exists` check |
| `Workflow timed out` | Long-running sync execution | Use `responseMode: "onReceived"` or increase timeout in settings |
| `401 Unauthorized` | Expired or misconfigured credential | Re-authenticate the credential in n8n Credentials |
| `Rate limit exceeded` | Too many API calls | Add Wait nodes or batch processing with delays |
| `ENOMEM` / out of memory | Workflow processing too many items | Add SplitInBatches or Limit node |
| `ECONNREFUSED` | Downstream service unreachable | Verify URL, network connectivity, and service health |

---

## Parallel Execution

### SplitInBatches Node

The primary mechanism for parallel processing in n8n. Configure `batchSize` and enable parallel execution via options:

```json
{
  "type": "n8n-nodes-base.splitInBatches",
  "name": "Batch 10",
  "parameters": {
    "batchSize": 10,
    "options": {
      "maxParallelBatches": 5
    }
  }
}
```

- **`batchSize`**: Number of items per batch.
- **`maxParallelBatches`** (available in n8n 1.80+): Maximum concurrent batch executions. Set to 1 for sequential.
- Each batch receives a subset of the input items. Downstream nodes process each batch independently.
- When `maxParallelBatches > 1`, n8n executes multiple branches of the workflow concurrently.

### Parallel HTTP Calls

To fire multiple API calls in parallel:

1. Use a Set or Code node to prepare an array of request configs.
2. Use the HTTP Request node in batch mode (when `method` and `url` use expressions referencing `$json`, each item triggers its own request).
3. Set `options.batching.batchSize` and `options.batching.batchInterval` to control parallelism.

### Code Node Parallel Execution

Inside a Code node (JavaScript), use `Promise.all`:

```javascript
const items = $input.all();
const promises = items.map(async (item) => {
  const response = await this.helpers.httpRequest({
    url: `https://api.example.com/data/${item.json.id}`,
    method: 'GET',
  });
  return { json: response };
});
return await Promise.all(promises);
```

**Important**: Each Code node execution is sandboxed. The `Promise.all` pattern above works within a single execution. For CPU-bound work, use SplitInBatches with `maxParallelBatches` to distribute across multiple process forks.

### Parallelism Pitfalls

- **Rate limiting**: Parallel requests can overwhelm downstream APIs. Add delays or throttle with batch intervals.
- **Race conditions on shared state**: `staticData` writes across parallel branches can conflict. Avoid writing to the same key from parallel branches.
- **Ordering**: Parallel batch execution does not guarantee output order. If order matters, use sequential batches (`maxParallelBatches: 1`).
- **Memory**: Each parallel execution fork consumes memory. Monitor n8n worker memory when using high `maxParallelBatches`.

---

## Integrations and Credentials

### Credential Architecture

n8n credentials are stored encrypted in the database and referenced by nodes via `credentials` blocks:

```json
{
  "type": "n8n-nodes-base.googleSheets",
  "name": "Google Sheets",
  "credentials": {
    "googleSheetsOAuth2Api": {
      "id": "credential-id-string",
      "name": "My Google Account"
    }
  }
}
```

Credentials support OAuth2, API Key, Basic Auth, Header Auth, and custom auth types depending on the node.

### Key Integration Nodes

| Integration | Node Type | Auth Method |
|-------------|-----------|------------|
| Google Sheets | `n8n-nodes-base.googleSheets` | OAuth2 |
| Gmail | `n8n-nodes-base.gmail` | OAuth2 |
| Slack | `n8n-nodes-base.slack` | OAuth2 / Bot Token |
| Telegram | `n8n-nodes-base.telegram` | Bot Token |
| Airtable | `n8n-nodes-base.airtable` | Personal Access Token |
| Notion | `n8n-nodes-base.notion` | Internal Integration Secret |
| PostgreSQL | `n8n-nodes-base.postgres` | Username/Password |
| MySQL | `n8n-nodes-base.mySql` | Username/Password |
| Redis | `n8n-nodes-base.redis` | Password |
| RabbitMQ | `n8n-nodes-base.rabbitmq` | Username/Password |
| OpenAI | `n8n-nodes-base.openAi` | API Key |
| AWS S3 | `n8n-nodes-base.awsS3` | Access Key + Secret |
| WhatsApp (Evolution) | Community/HTTP | API Key |
| Webflow | `n8n-nodes-base.webflow` | OAuth2 |

### HTTP Request Node as Universal Connector

For any API without a dedicated n8n node, use the HTTP Request node with generic credential type:

```json
{
  "type": "n8n-nodes-base.httpRequest",
  "name": "Custom API",
  "parameters": {
    "method": "POST",
    "url": "https://api.service.com/v1/endpoint",
    "authentication": "genericCredentialType",
    "genericAuthType": "httpHeaderAuth",
    "sendHeaders": {
      "parameters": [
        { "name": "X-API-Key", "value": "={{ $credentials.apiKey }}" }
      ]
    },
    "sendBody": true,
    "bodyParameters": {
      "parameters": [
        { "name": "data", "value": "={{ JSON.stringify($json) }}" }
      ]
    }
  }
}
```

---

## Best Practices

### Workflow Design

1. **Single Responsibility**: Each workflow should perform one logical operation. Compose complex processes via `executeWorkflow` sub-workflow calls instead of monolithic workflows.

2. **Naming Conventions**: Use descriptive node names that indicate function, not type. Prefer "Fetch Customer" over "HTTP Request1". Use PascalCase or Sentence case consistently.

3. **Node Positioning**: Arrange nodes left-to-right or top-to-bottom. Place triggers on the left. Group related logic. Use Sticky Notes for documentation.

4. **Limit Node Count**: Workflows with more than 50 nodes become hard to debug. Split into sub-workflows.

5. **Tagging**: Tag workflows by purpose (`#production`, `#dev`, `#sales`, `#ops`) and by integration (`#slack`, `#sheets`).

### Data Handling

6. **Validate Input Early**: Place an IF node after triggers to validate required fields before processing. Reject malformed data at the boundary.

7. **Use `??` and `||` Liberally**: Always provide fallback values for optional fields. Expressions like `{{ $json.name ?? "Unknown" }}` prevent null-propagating errors.

8. **Return Only Needed Fields**: After HTTP calls or database queries, use a Set node to pluck only the fields downstream nodes need. This keeps data items lean and reduces memory pressure.

9. **Pin Data for Testing**: Use pin data (right-click any node -> "Pin output") during development to iterate on downstream logic without re-running upstream calls.

### Error Handling and Resilience

10. **Every Production Workflow Needs an Error Workflow**: Bind error workflows that log failures to Slack, email, or a monitoring system. At minimum, log the `error.message`, `error.node`, and `execution.id`.

11. **Set Timeouts Appropriately**: In `settings.executionTimeout`, set a timeout slightly above your expected worst-case execution time. The default is -1 (no limit), which can lead to stuck executions.

12. **Handle Rate Limits Proactively**: Insert Wait nodes between batch API calls. For APIs with known rate limits, calculate the required delay and space requests accordingly.

13. **Use `staticData` Sparingly**: `staticData` persists across runs but is workflow-scoped. It is not a database — do not store more than a few KB. For persistent state, use a proper database or Redis.

### Performance

14. **Batch API Calls**: When processing many items that each need an API call, use SplitInBatches with `maxParallelBatches` instead of sequential HTTP Request calls.

15. **Avoid Nested Loops in Code Nodes**: If you need nested iteration, prefer chaining multiple nodes (SplitInBatches, then another SplitInBatches) over nested `for` loops in Function nodes — it is easier to debug and benefits from n8n's parallelisation.

16. **Use FunctionItem for Simple Transformations**: FunctionItem nodes run once per item and are lighter than Function nodes that receive all items. If your transformation does not need item cross-referencing, use FunctionItem.

### Security

17. **Webhook Authentication Always On**: Production webhooks must require authentication (header auth or basic auth). Never expose an unauthenticated webhook to the public internet.

18. **Rotate Credentials**: For API key-based auth, rotate keys periodically. n8n's credential system supports updating without touching workflows.

19. **Environment Variables for Secrets**: Use `{{ $env.VARIABLE_NAME }}` in expressions to reference environment variables. Keep secrets out of workflow JSON exports.

20. **Workflow Sharing**: When exporting workflows for sharing (e.g., community nodes, templates), always strip credential references. Use the workflow export tool that omits credential IDs.

---

## Workflow Diagnostics

### Systematic Debugging Process

When a workflow fails or behaves unexpectedly, follow this structured diagnostic approach:

#### Step 1: Identify the Failing Node

- Open the n8n execution history and find the failed execution.
- Note the node name where execution stopped (red X marker).
- Check the execution log for the error message and stack trace.

#### Step 2: Inspect Input Data

- In the execution view, click the failing node to see its "Input" tab.
- Verify the input data shape matches what the node expects.
- Check for `undefined`, `null`, or missing fields that the node's expressions reference.
- If input data looks correct, the issue may be in the node's configuration.

#### Step 3: Validate Expressions

- Copy each expression from the node's parameters and evaluate mentally against the input data.
- Common expression bugs:
  - Typo in field name (`email` vs `Email` vs `e-mail`)
  - Wrong node reference (`$node["Wrong Name"]`)
  - Array accessed as object (`$json.items.field` when `items` is an array)
  - Missing fallback for optional fields
  - Incorrect DateTime format string

#### Step 4: Trace Item Count Flow

- Check how many items enter and exit each node.
- A node producing 0 output items breaks downstream nodes that expect data.
- A node producing more items than expected (e.g., HTTP Request fan-out) may cause memory pressure.
- Use the execution view's item count display to spot unexpected shrinkage or growth.

#### Step 5: Isolate and Reproduce

- Disconnect downstream nodes and re-run the workflow up to the suspect node.
- Use pin data on the suspect node's output to test downstream nodes independently.
- If the workflow involves external APIs, use the HTTP Request node in "test" mode or replace it with a Set node returning mock data.

### Common Configuration Errors

#### Webhook Not Triggering

- **Symptom**: Webhook URL returns 404 or no response.
- **Checks**:
  1. Is the workflow set to "Active"? Production webhooks require active status.
  2. Are you using the correct URL? Test webhook is `/webhook-test/<path>`, production is `/webhook/<path>`.
  3. Does the HTTP method match? A webhook configured for POST returns 404 for GET.
  4. Is the `path` parameter set and unique? Conflicting paths cause issues.
  5. Check n8n server logs for webhook registration errors.

#### HTTP Request Returning Unexpected Status

- **Symptom**: API returns 4xx or 5xx.
- **Checks**:
  1. Verify the URL uses correct protocol (http vs https).
  2. Check headers: Content-Type, Authorization, Accept.
  3. Inspect the actual request body sent (check node output in execution history).
  4. If using expressions in URL or body, verify they evaluate to expected values.
  5. Test the same request with curl or Postman to isolate n8n vs API issue.

#### IF/Switch Node Not Routing as Expected

- **Symptom**: Items go to the wrong branch or none.
- **Checks**:
  1. Print the comparison values: insert a Set node before the condition that logs the field.
  2. For IF: verify `combinator` is correct (`and` vs `or`).
  3. For Switch: verify the `dataPropertyName` field exists at the top level of `$json`.
  4. Check operator type: comparing a number as a string type fails silently.
  5. Verify the condition value type: `"5"` (string) vs `5` (number) vs `true` (boolean).

#### Code Node Throwing Unexpected Errors

- **Symptom**: Code node fails with syntax or runtime error.
- **Checks**:
  1. Syntax: missing semicolons, unmatched braces, incorrect arrow function syntax.
  2. Async: if using `await`, the function must be `async`.
  3. Sandbox limits: Code nodes have no `require()`, no `fs`, no `process`. Only `this.helpers` is available.
  4. Lodash and Luxon are available globally as `_` and `DateTime`/`luxon`.
  5. In Python Code nodes: only `numpy` and standard library are available by default; `requests` is not available — use `this.helpers.httpRequest` equivalent.

### Performance Diagnostics

#### Slow Workflow Execution

- **Checklist**:
  1. Identify the slowest node from execution timing display.
  2. HTTP Request nodes: check API response time. Add caching (`options.ttl`) if data changes infrequently.
  3. Code nodes: profile with `console.time()` / `console.timeEnd()` to find bottlenecks.
  4. Database queries: verify indexes exist on filtered/joined columns.
  5. Large item arrays: add Limit or SplitInBatches nodes to control memory.
  6. Sequential HTTP calls: parallelise with SplitInBatches + `maxParallelBatches`.
  7. Remove unnecessary node chains: each node adds overhead.

#### Memory Issues

- **Symptoms**: `ENOMEM`, worker crashes, very slow execution.
- **Checks**:
  1. How many items flow through? Use a Limit node to cap during testing.
  2. Are binary data items large? Binary data is stored differently and can exhaust memory.
  3. Reduce `batchSize` in SplitInBatches.
  4. Check for nodes that explode item count (e.g., HTTP Request fan-out without a Limit).
  5. Monitor n8n worker memory in system metrics and consider scaling workers horizontally.

### Diagnostic Script

The `scripts/n8n_validate.py` tool validates n8n workflow JSON files for structural correctness. Run it against a workflow export to catch schema-level issues before deployment:

```bash
python3 scripts/n8n_validate.py workflow.json
```

It checks for:
- Valid JSON syntax
- Presence of required top-level keys (`name`, `nodes`, `connections`)
- Each node has required fields (`type`, `name`, `position`)
- Connections reference existing node names (no dangling edges)
- Webhook nodes have a `path` parameter
- Trigger nodes appear as workflow entry points (no inbound connections)

---

## References

- [n8n Official Documentation](https://docs.n8n.io/)
- [n8n Community Forum](https://community.n8n.io/)
- [n8n Workflow Templates](https://n8n.io/workflows/)
- [n8n Node Code Reference (GitHub)](https://github.com/n8n-io/n8n/tree/master/packages/nodes-base/nodes)
