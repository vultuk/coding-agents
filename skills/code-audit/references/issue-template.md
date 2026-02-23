# Individual Issue Template

Use this structure for individual recommendation issues.

## Format

```markdown
## Summary

[1-2 sentence description of the issue and why it matters]

## Recommendation from Audit

> [Quote the exact recommendation from the audit report]

## Details

[Detailed explanation including:]
- What is currently happening
- Why it's a problem
- Affected files/components

## Suggested Implementation

[Concrete implementation guidance]

### Option 1: [Approach Name]

\`\`\`[language]
// Example code
\`\`\`

## Acceptance Criteria

- [ ] [Specific criterion]
- [ ] Tests added/updated
- [ ] Documentation updated (if applicable)

## Related

- Audit Report: (will be linked from main audit)
- Related files: `path/to/file.py`
```

## Example

```markdown
## Summary

The FIX market data service would benefit from comprehensive metrics and observability instrumentation to improve operational visibility and debugging capabilities.

## Recommendation from Audit

> Add metrics/observability - improve operations

## Suggested Metrics

### Connection Metrics
- `fix_connection_status` (gauge): Current connection state
- `fix_reconnection_total` (counter): Reconnection attempts

### Message Metrics
- `fix_messages_received_total` (counter, labels: msg_type): Messages by type
- `fix_message_processing_seconds` (histogram): Processing latency

## Suggested Implementation

### Option 1: Prometheus Client

\`\`\`python
from prometheus_client import Counter, Gauge, Histogram

messages_received = Counter(
    'fix_messages_received_total',
    'Total FIX messages received',
    ['msg_type']
)

message_latency = Histogram(
    'fix_message_processing_seconds',
    'Message processing latency',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)
\`\`\`

## Acceptance Criteria

- [ ] Prometheus metrics endpoint at `/metrics`
- [ ] Connection, message, and error metrics implemented
- [ ] Grafana dashboard created

## Related

- Related files: `fix_client.py`, `main.py`
```

## Guidelines

1. **Summary**: Brief but explain the value
2. **Quote**: Always quote the exact audit recommendation
3. **Implementation**: Provide concrete, copy-paste-ready code
4. **Acceptance Criteria**: Specific and testable
