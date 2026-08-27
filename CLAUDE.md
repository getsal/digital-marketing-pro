# digital-marketing-pro

**The most comprehensive digital marketing plugin for Claude Code and Claude Cowork** — 25 specialist agents, 149 skills, and the 12-Part Engagement Methodology for end-to-end client engagements.

This plugin orchestrates the full digital marketing lifecycle: from Stone-vs-Opinion intake and unbiased external research, through the Four Core Documents, client validation, and channel strategy fan-out, to execution, reporting, and continuous improvement. Designed for agencies and in-house teams managing multi-channel campaigns across SEO, paid media, social, email, CRO, and more.

Current version: **3.2.0**. Repository: https://github.com/indranilbanerjee/digital-marketing-pro

## Core Capabilities

### Strategy & Planning
- **/digital-marketing-pro:brand-setup** — Intake brand identity, audience, and positioning
- **/digital-marketing-pro:four-core-documents** — Build the canonical strategy foundation (61 steps)
- **/digital-marketing-pro:campaign-plan** — Plan multi-channel campaigns with budget allocation
- **/digital-marketing-pro:growth-plan** — Build growth roadmap and yearly planner
- **/digital-marketing-pro:yearly-planner** — Annual marketing calendar and initiative planning

### SEO & Content
- **/digital-marketing-pro:seo-plan** — Comprehensive SEO strategy with AEO/GEO readiness
- **/digital-marketing-pro:seo-audit** — Full technical + content SEO audit
- **/digital-marketing-pro:tech-seo-audit** — Technical SEO deep-dive
- **/digital-marketing-pro:keyword-research** — Keyword discovery and mapping
- **/digital-marketing-pro:content-engine** — Content production workflow
- **/digital-marketing-pro:content-brief** — Brief-to-article pipeline
- **/digital-marketing-pro:programmatic-seo** — Scale SEO pages from structured data

### Analytics & Reporting
- **/digital-marketing-pro:performance-report** — Campaign performance reports
- **/digital-marketing-pro:analytics-insights** — Data analysis and insights
- **/digital-marketing-pro:attribution-report** — Multi-touch attribution
- **/digital-marketing-pro:roi-calculator** — ROI and ROAS modeling
- **/digital-marketing-pro:executive-dashboard** — Exec-level KPI view

### Quality & Compliance
- **/digital-marketing-pro:check** — Pre-publish brand + hallucination gate (replaces global hook)
- **/digital-marketing-pro:validate-output** — Output quality validation
- **/digital-marketing-pro:verify-claims** — Fact-check marketing claims
- **/digital-marketing-pro:status** — On-demand brand snapshot and engagement status

### Agency Operations
- **/digital-marketing-pro:client-onboarding** — New client intake workflow
- **/digital-marketing-pro:client-report** — Client-ready report generation
- **/digital-marketing-pro:switch-brand** — Switch active brand/client context
- **/digital-marketing-pro:agency-dashboard** — Portfolio-level agency view

### All 149 Skills
See `skills/` directory. Each skill is invocable as `/digital-marketing-pro:<skill-name>`.

## Artifact Dependency Graph

```yaml
artifacts:
  - name: brand-memory (Living Project Instruction File)
    mode: prescriptive
    direction: source

  - name: four-core-documents (v1)
    mode: prescriptive
    direction: target
    sources: [brand-setup, stone-vs-opinion-intake]

  - name: client-validation-document (v2 trigger)
    mode: prescriptive
    direction: target
    sources: [four-core-documents]

  - name: four-core-documents (v2)
    mode: prescriptive
    direction: target
    sources: [client-validation-document]

  - name: execution-artefacts
    mode: descriptive
    direction: target
    sources: [four-core-documents (v2), campaign-plan, channel-strategy]

sync_skills:
  brand-setup: → brand-memory
  four-core-documents: brand-memory → four-core-documents (v1)
  client-validation-document: four-core-documents (v1) → client-validation-document
  campaign-plan: four-core-documents (v2) → execution-artefacts
  update-back-rule: execution-artefacts → brand-memory (versioned corrections)
```

Direction rules: v1 documents (unbiased research) are never deleted. v2 re-runs only the documents flagged by the Decision Matrix. The Living Project Instruction File is always updated last.

## Recommended Schedules

| Skill | Schedule | Purpose |
|-------|----------|---------|
| rank-monitor | daily | Track keyword ranking changes |
| competitor-monitor | daily | Detect competitor changes |
| performance-check | daily | Alert on metric anomalies |
| anomaly-scan | every 6h | Detect traffic/conversion spikes or drops |
| serp-tracker | weekly | Weekly SERP position report |
| content-decay-scan | weekly | Find pages with declining traffic |
| share-of-voice | weekly | Brand vs competitor SOV |
| autopilot-status | weekly | Campaign health summary |
| competitor-alerts | weekly | Competitor activity digest |

To schedule: use `mcp__trinity__create_agent_schedule`.

## Guidelines

1. **Run `/check` before publishing** — replaces the removed global PreToolUse hook. Any content write touching a client asset must pass the brand + hallucination gate first.
2. **Living Project Instruction File is source of truth** — all skills read it first. When live operations surface corrections, apply the Update-Back Rule immediately (version the source docs, then propagate).
3. **v1 is never deleted** — the unbiased market view stays intact even after client validation produces v2. Stress-testing always references v1.
4. **Stone vs Opinion discipline** — at intake, tag every fact. Stone = client knows for certain. Opinion = client believes → becomes a research question, not ground truth for campaign decisions.
