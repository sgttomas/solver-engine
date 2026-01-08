# SOLVER Business Model v1.0

**Document Type:** Business Strategy
**Status:** Draft
**Author:** Ryan Tufts (Architect)
**Date:** 2025-01-07

---

## 1. Executive Summary

SOLVER's architecture enables a unique value proposition: **methodology as a moat**. As organizations use SOLVER, they accumulate domain-specific methodology templates that become increasingly valuable over time. This creates network effects and defensible switching costs.

This document captures business model concepts to inform architectural decisions. Technical implementation details remain in the [Expansion Roadmap](../spec/10_SOLVER-Expansion-Roadmap-v1.0.md).

---

## 2. Core Value Proposition

### 2.1 The Methodology Library Moat

**Conjecture:** Cached methodology documents for similar problem types become more valuable over time.

**Evidence (to be validated post-MVP):**
- V3 methodologies represent refined thinking through V1→V2→V3 iteration
- Successful methodologies (high approval rate, low revision count) indicate quality
- Domain experts encode tacit knowledge into templates
- Organizations accumulate proprietary problem-solving approaches

**Network Effect Dynamics:**
```
More workflows → More methodologies → Better suggestions → More value → More workflows
```

### 2.2 Value Layers

| Layer | Value | Who Captures It |
|-------|-------|-----------------|
| **Execution** | Run workflows on problems | SOLVER platform |
| **Methodology** | Curated approaches by problem type | Experts, organizations |
| **Knowledge Graph** | Cross-workflow intelligence | Platform + users |
| **Audit Trail** | Compliance, accountability | Organizations |

---

## 3. Revenue Model Options

### 3.1 SaaS + Marketplace Hybrid (Recommended)

| Revenue Stream | Description | Example Pricing |
|----------------|-------------|-----------------|
| **Core SaaS** | Per-workflow execution | $10-50/workflow (depends on steps) |
| **Methodology Library Access** | Subscription to curated methodologies | $99-499/org/month |
| **Private Methodology Hosting** | Organization's proprietary library | $999-2499/org/month |
| **Methodology Marketplace** | Experts sell domain-specific methodologies | 70/30 revenue split |
| **Enterprise License** | Self-hosted + private library | $50k-200k/year |

### 3.2 Freemium Model

| Tier | Features | Price |
|------|----------|-------|
| **Free** | Public methodologies (community-contributed), limited workflows | $0 |
| **Pro** | Curated expert methodologies + private methodology storage | $49/user/month |
| **Team** | Shared org library + collaboration | $199/team/month |
| **Enterprise** | Self-hosted + SSO + dedicated support | Custom |

### 3.3 Usage-Based Pricing

| Metric | Rationale |
|--------|-----------|
| Per workflow | Simple, predictable |
| Per step executed | Granular, reflects actual usage |
| Per artifact approved | Aligns cost with value delivered |
| Per methodology retrieval | Charges for library value |

---

## 4. Instance N as Revenue Driver

### 4.1 Domain Specialization Packs

SOLVER's Instance hierarchy enables domain-specific offerings:

| Instance | Domain | Example Methodologies |
|----------|--------|----------------------|
| N=2 | Healthcare | HIPAA compliance analysis, clinical trial design |
| N=3 | Finance | Risk assessment, regulatory filing |
| N=4 | Legal | Contract analysis, due diligence |
| N=5 | Software | Architecture review, security audit |
| N=6 | Engineering | Safety analysis, design verification |

**Pricing Model:** Domain packs as add-on subscriptions ($99-499/domain/month)

### 4.2 Expert Contribution Model

Domain experts can contribute methodologies:

```
Expert creates methodology → Submits to marketplace → SOLVER reviews/curates
                                                            ↓
                           Expert gets 70% of revenue ← Users purchase access
```

**Quality Signals for Expert Ranking:**
- Approval rate (how often artifacts get approved first try)
- Revision count (lower is better)
- Time to approval (faster is better)
- User ratings (5-star system)
- Usage count (popularity)

---

## 5. Network Effects Playbook

### Phase 1: Seed the Library (Months 1-6)

**Goal:** Create critical mass of high-quality methodologies

**Actions:**
1. Manually create 20-30 methodologies for common problem types
2. Target specific verticals (e.g., "fintech backend engineering")
3. Offer free to early adopters in exchange for feedback
4. Track quality signals from actual usage

**Success Metrics:**
- 20+ methodologies with >80% approval rate
- 100+ workflows executed using seeded methodologies
- 3+ verticals with domain coverage

### Phase 2: Community Contribution (Months 6-12)

**Goal:** Enable organic methodology growth

**Actions:**
1. Launch methodology submission workflow
2. Invite domain experts to contribute (paid per usage)
3. Build reputation system (ratings, usage counts, expert badges)
4. Curate and promote top methodologies

**Success Metrics:**
- 50+ community-contributed methodologies
- 10+ verified domain experts
- Organic methodology discovery (users finding relevant approaches)

### Phase 3: Proprietary Libraries (Year 2+)

**Goal:** Create switching costs through accumulated knowledge

**Actions:**
1. Enable private organizational libraries
2. Track methodology lineage (how org methodologies evolve)
3. Provide analytics on methodology effectiveness
4. Offer migration tools from competitors

**Success Metrics:**
- Organizations with 50+ proprietary methodologies
- <5% annual churn (switching costs work)
- Methodology improvement trends (V1→VN within org)

---

## 6. Competitive Positioning

### 6.1 vs. Generic LLM Tools (ChatGPT, Claude, etc.)

| Aspect | Generic LLM | SOLVER |
|--------|-------------|--------|
| **Workflow** | Freeform | Structured 10-step |
| **Human Gates** | None | Mandatory |
| **Audit Trail** | None | Full provenance |
| **Methodology Reuse** | None | Library + patterns |
| **Domain Knowledge** | General | Specialized via Instance N |

**Positioning:** "SOLVER is what you use when the answer matters."

### 6.2 vs. Workflow Engines (Zapier, n8n, etc.)

| Aspect | Workflow Engine | SOLVER |
|--------|-----------------|--------|
| **Focus** | Task automation | Knowledge work |
| **Human Role** | Trigger/approve | Deep review + judgment |
| **Output** | Actions executed | Specifications produced |
| **Learning** | None | Methodology improvement |

**Positioning:** "SOLVER thinks; workflow engines do."

### 6.3 vs. Knowledge Management (Notion, Confluence)

| Aspect | Knowledge Mgmt | SOLVER |
|--------|----------------|--------|
| **Structure** | User-defined | Methodology-enforced |
| **Traceability** | Manual links | Automatic lineage |
| **Quality** | Varies | Judge-validated |
| **Reuse** | Copy-paste | Pattern retrieval |

**Positioning:** "SOLVER produces knowledge; others store it."

---

## 7. Go-to-Market Strategy

### 7.1 Initial Target Segments

| Segment | Pain Point | Value Prop |
|---------|------------|------------|
| **Compliance teams** | Audit trail requirements | Full provenance, gate enforcement |
| **Architecture reviewers** | Inconsistent review quality | Methodology templates, structured output |
| **Product managers** | Requirements drift | Traceability, staleness detection |
| **Legal/regulatory** | Human accountability required | Judge framework, approval gates |

### 7.2 Land and Expand

```
Land: Single team uses SOLVER for specific problem type
       ↓
Expand: Team accumulates methodologies, shares internally
        ↓
Enterprise: Organization standardizes on SOLVER, builds private library
            ↓
Lock-in: Switching costs from accumulated methodology investment
```

---

## 8. Architectural Requirements (from Business Model)

These business model concepts inform technical architecture:

| Business Need | Technical Requirement |
|---------------|----------------------|
| Methodology caching | `problem_type` field, pgvector similarity |
| Quality signals | Track `approval_rate`, `revision_count`, `time_to_approval` |
| Expert marketplace | Methodology ownership, revenue attribution |
| Private libraries | Multi-tenant isolation, org-level access control |
| Usage-based pricing | Workflow/step/artifact metering |
| Network effects | Cross-workflow methodology discovery |

See [Expansion Roadmap PS1](../spec/10_SOLVER-Expansion-Roadmap-v1.0.md#2-problem-statement-1-knowledge-graph-integration) for technical implementation.

---

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Methodology quality varies** | Poor suggestions erode trust | Curation, quality signals, expert verification |
| **Cold start problem** | No methodologies = no value | Seed library manually before launch |
| **Switching costs too weak** | Easy churn | Export restrictions? Or: make value so high switching is irrational |
| **Commoditization** | LLM providers add similar features | Methodology moat, domain depth, enterprise features |
| **Expert supply** | Not enough contributors | Revenue share, reputation system, badges |

---

## 10. Success Metrics

### 10.1 Product-Market Fit Indicators

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Workflow completion rate** | >80% | Users find value in completing workflows |
| **Methodology reuse rate** | >30% | Library provides value |
| **Approval rate (first try)** | >60% | Methodologies produce quality output |
| **NPS** | >40 | Users recommend SOLVER |

### 10.2 Business Health Indicators

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Monthly recurring revenue** | Growth >10%/month | Sustainable business |
| **Net revenue retention** | >120% | Expansion exceeds churn |
| **Payback period** | <12 months | Efficient customer acquisition |
| **Methodology library growth** | >20/month | Network effects working |

---

## 11. Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-07 | Ryan Tufts | Initial draft |
