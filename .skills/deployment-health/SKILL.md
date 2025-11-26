---
name: deployment-health
description: Check Render deployment health, service status, errors, and logs for Surf Lamp services
tags: [deployment, render, monitoring, debugging, production]
---

# Deployment Health Checker

When user asks about deployment status, service health, or production issues, use this workflow:

## 1. Quick Health Overview

Start with a comprehensive services check:
```
Use: mcp__render__render_services_status
Parameters: analysis_level="summary"
```

This provides:
- All services status (web, background, Redis)
- Recent deployment info
- Error counts
- Cost overview

## 2. Deep Dive (If Issues Found)

If errors or problems detected, investigate further:

### A. Service Events Analysis
```
Use: mcp__render__render_service_events
Parameters:
  - service_id=null (uses default)
  - limit=20
```

Provides:
- Actionable insights
- Categorized problems
- Recommended fixes

### B. Recent Deployment Logs
```
Use: mcp__render__render_latest_deployment_logs
Parameters:
  - service_id=null
  - lines=30
```

Checks for deployment failures, build errors, startup issues.

### C. Recent Errors
```
Use: mcp__render__render_recent_errors
Parameters:
  - service_id=null
  - limit=50
  - service_type="web" or "background"
```

Filters logs for ERROR and WARNING levels only.

### D. Search Specific Issues
```
Use: mcp__render__search_render_logs
Parameters:
  - search_term="timeout" | "OpenWeatherMap" | "429" | etc.
  - limit=20
  - service_type="web" or "background"
```

## 3. Deployment History

For deployment timeline and patterns:
```
Use: mcp__render__render_deployments
Parameters:
  - service_id=null (defaults to first web service)
  - limit=10
```

Shows:
- Recent deployment status (live, failed, building)
- Build durations
- Commit messages
- Timestamps (UTC - add 3 hours for Israel time)

## 4. Specific Service Check

For individual service deep dive:
```
Use: mcp__render__render_service_status
Parameters: service_id=null
```

Returns:
- Service configuration
- Current health
- Environment details

## Multi-Service Architecture Notes

Surf Lamp has TWO web services:
- `final-surf-lamp-web` (srv-ctkq2vbqf0us73a8lvb0) - Main dashboard + Arduino API
- `surf-lamp-viz` (srv-ctkq0rug3zdc738ghs7g) - System visualizer only

When checking Arduino issues, ALWAYS use `final-surf-lamp-web` service logs.

## Key Insights to Provide

1. **Deployment Status**: Live/failed/building
2. **Error Patterns**: Rate limiting, timeouts, OOM, API failures
3. **Service Health**: All services running or any down
4. **Recent Changes**: What was deployed and when
5. **Action Items**: Specific fixes needed (if any)

## Response Format

Provide:
- **Status Summary**: One-line overall health
- **Services Overview**: Quick status of all services
- **Recent Activity**: Last deployment, recent errors
- **Issues Found**: Categorized problems with severity
- **Recommended Actions**: Specific next steps (if needed)

Keep responses concise. Only deep dive if issues found.
