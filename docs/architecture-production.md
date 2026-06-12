# Architecture — Production target (post-MVP, if demo approved)

Same domain objects as the MVP (PRD §11 report contract) — production swaps
the *sinks*, not the model. Migration = write the same objects to Postgres/S3
instead of session state. Drawn for the roadmap discussion; build only when a
real constraint appears.

```mermaid
flowchart TB
    subgraph clients["Clients (firm-scoped tenants)"]
        WEB[Web app<br/>React/Next.js]
        API_C[API clients<br/>firm integrations]
    end

    subgraph edge["Edge"]
        AUTH[Auth + multi-tenancy<br/>firm-level isolation, RBAC<br/>lifts MVP non-goal N7]
        GW[API gateway / FastAPI]
    end

    subgraph core["Core services"]
        ING[Ingestion service<br/>rasterize, page mgmt,<br/>multi-sheet sets — roadmap R3]
        EXTS[Extraction service<br/>provider-routed vision LLM<br/>confidence + crops]
        GATE2[Confirmation workflow<br/>same FR-5 gate, async review queue]
        ENG2[Rule engine service<br/>same simpleeval core<br/>pack resolved by jurisdiction + effective date]
        REP[Report service<br/>PDF/HTML render, share links]
    end

    subgraph rulemgmt["Rule-pack management (roadmap R4)"]
        EDITOR[Pack editor UI<br/>domain-expert owned]
        CHLOG[Change log + gazette diff<br/>VERIFY resolution workflow]
        PACKDB[(Versioned packs<br/>effective-date queries)]
    end

    subgraph data["Data layer"]
        PG[(Postgres<br/>submissions, params, findings,<br/>append-only audit events)]
        S3[(Object storage S3/R2<br/>PDFs + crops, per-client encryption,<br/>configurable retention/TTL)]
        EVAL[(Eval store<br/>labeled set, recall/precision per release)]
    end

    subgraph llm2["LLM providers (no-training tier)"]
        C2[Claude]
        G2[Gemini]
    end

    WEB --> AUTH --> GW
    API_C --> AUTH
    GW --> ING --> EXTS
    EXTS --> C2
    EXTS -.-> G2
    EXTS --> GATE2 --> ENG2 --> REP
    EDITOR --> CHLOG --> PACKDB --> ENG2
    ING --> S3
    EXTS --> S3
    GATE2 --> PG
    ENG2 --> PG
    REP --> PG
    ENG2 --> EVAL
    REP --> WEB
```

## What changes vs MVP — and what must not

| Concern | MVP | Production |
|---|---|---|
| Persistence | session-only | Postgres (append-only audit events — legal artifact) + S3 with configurable retention |
| Access | shared password | per-firm auth, tenant isolation (hard requirement — drawings commercially sensitive) |
| Rule packs | YAML in repo | DB-backed + expert editor, changelog, gazette diff (R4) |
| Stack | Streamlit monolith | API + workers + SPA — only when multi-user/UX demands it |
| Scope | single sheet, A-3 only | multi-sheet sets (R3), more occupancies (R2), geometry Tier-2 (R1) |
| Eval | manual script | recall/precision tracked per release against labeled set; release gate = life-safety recall ≥ 0.90 |

**Must not change:** the FR-5 confirmation gate, FR-9 no-silent-pass, the
BNBC/RAJUK jurisdiction split, the non-certification disclaimer, and the PRD
§11 object shapes (they are the migration contract).

**Explicitly still out** (separate product track): structural/seismic review
(R5) — different discipline, different liability surface.
