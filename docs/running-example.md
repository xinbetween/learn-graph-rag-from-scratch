# Running example: the Kestrel Labs corpus

Every chapter, exercise and capstone uses this one fictional world, so learners can see the
same graph grow from raw text to communities to answers. All of it is made up.

## Entities (canonical names and types)

| Name | Type | Notes |
|---|---|---|
| Kestrel Labs | ORGANIZATION | Ocean-tech startup in Port Avalon. Builds autonomous underwater drones. Founded 2021. |
| Dr. Mira Okafor | PERSON | Co-founder and CEO of Kestrel Labs. Formerly a senior researcher at Tidewater Institute (2015–2021). Aliases: "Mira Okafor", "Okafor", "the CEO". |
| Jonas Vehl | PERSON | Co-founder and CTO of Kestrel Labs, 2021 to March 2026. Designed the Sentinel sonar array. Stepped down as CTO in March 2026 and became Chief Scientist. Alias: "Vehl". |
| Priya Nair | PERSON | Joined Kestrel Labs from Marlow Dynamics in 2023. Lead engineer on Project Sentinel, co-lead of Project Tern. Became CTO in March 2026. |
| Tidewater Institute | ORGANIZATION | Marine research institute in Port Avalon. Research partner on Project Sentinel. Alias: "Tidewater", "TWI". |
| Dr. Ana Ruiz | PERSON | Director of Tidewater Institute. Principal investigator of the Halden Reef survey. |
| Project Sentinel | PROJECT | Kestrel's reef-monitoring drone program, launched 2023 with Tidewater Institute. Alias: "Sentinel", "Sentinel drones". |
| Project Tern | PROJECT | In-house sonar module started in mid-2025 to replace Deepcast sonar. Led by Jonas Vehl and Priya Nair. Alias: "Tern". |
| Halden Reef | LOCATION | Coral reef 40 km off Port Avalon. |
| Port Avalon | LOCATION | Coastal city; home of Kestrel Labs and Tidewater Institute. |
| 2024 Halden Reef bleaching event | EVENT | Mass coral bleaching first detected by Sentinel drones in August 2024. |
| Brightwater Capital | ORGANIZATION | Venture firm. Led Kestrel's Series A (2022, $12M) and Series B (2025, $40M). |
| Lena Park | PERSON | Partner at Brightwater Capital; sits on Kestrel Labs' board. |
| Marlow Dynamics | ORGANIZATION | Competitor building defense-focused underwater vehicles. Acquired Deepcast in April 2025. |
| Deepcast | ORGANIZATION | Sonar hardware supplier. Supplied Kestrel Labs until Marlow Dynamics acquired it and ended outside contracts. |
| Ocean Health Act | LAW | Regional regulation passed in 2025 requiring quarterly reef monitoring; created demand for Sentinel. |
| Port Avalon City Council | ORGANIZATION | Contracted Kestrel Labs in late 2025 for Ocean Health Act compliance monitoring. |

## Key relationships (source, relation, target, time)

- Dr. Mira Okafor — CO_FOUNDED — Kestrel Labs (2021)
- Jonas Vehl — CO_FOUNDED — Kestrel Labs (2021)
- Dr. Mira Okafor — CEO_OF — Kestrel Labs (2021–)
- Jonas Vehl — CTO_OF — Kestrel Labs (2021–2026-03)
- Priya Nair — CTO_OF — Kestrel Labs (2026-03–)
- Dr. Mira Okafor — FORMERLY_WORKED_AT — Tidewater Institute (2015–2021)
- Priya Nair — FORMERLY_WORKED_AT — Marlow Dynamics (–2023)
- Dr. Ana Ruiz — DIRECTS — Tidewater Institute
- Kestrel Labs — RUNS — Project Sentinel (2023–)
- Tidewater Institute — PARTNERS_ON — Project Sentinel
- Priya Nair — LEADS — Project Sentinel
- Project Sentinel — MONITORS — Halden Reef
- Project Sentinel — DETECTED — 2024 Halden Reef bleaching event (2024-08)
- 2024 Halden Reef bleaching event — OCCURRED_AT — Halden Reef
- Dr. Ana Ruiz — LEADS_SURVEY_OF — Halden Reef
- Brightwater Capital — INVESTED_IN — Kestrel Labs (Series A 2022, Series B 2025)
- Lena Park — PARTNER_AT — Brightwater Capital
- Lena Park — BOARD_MEMBER_OF — Kestrel Labs
- Deepcast — SUPPLIED — Kestrel Labs (2022–2025)
- Marlow Dynamics — ACQUIRED — Deepcast (2025-04)
- Marlow Dynamics — COMPETES_WITH — Kestrel Labs
- Kestrel Labs — RUNS — Project Tern (2025-06–)
- Jonas Vehl — CO_LEADS — Project Tern
- Priya Nair — CO_LEADS — Project Tern
- Project Tern — REPLACES — Deepcast sonar in Project Sentinel
- Ocean Health Act — REQUIRES — reef monitoring (drives demand for Project Sentinel)
- Port Avalon City Council — CONTRACTED — Kestrel Labs (2025-11)
- Kestrel Labs, Tidewater Institute, Port Avalon City Council — LOCATED_IN — Port Avalon

## Canonical questions used across the course

Multi-hop (vector RAG struggles):
1. "Why did Kestrel Labs start Project Tern?" → Marlow Dynamics acquired Deepcast → Deepcast stopped supplying Kestrel → Kestrel built its own sonar (Tern).
2. "Which investor's board member oversees the company whose drones detected the Halden Reef bleaching?" → Sentinel → Kestrel Labs → Lena Park (Brightwater Capital).
3. "What connects Priya Nair to Deepcast?" → Priya formerly at Marlow Dynamics, which acquired Deepcast; she co-leads Tern, which replaces Deepcast sonar.

Global / sensemaking (needs community summaries):
4. "What are the main themes in this corpus?" → reef science and monitoring; supply-chain risk and vertical integration; funding and growth; regulation creating demand.
5. "What risks does Kestrel Labs face?"

Temporal:
6. "Who is the CTO of Kestrel Labs?" → Priya Nair since March 2026 (Jonas Vehl before that).
7. "Who supplied Kestrel's sonar in 2024?" → Deepcast.

Expected communities (roughly): {Kestrel Labs, Mira Okafor, Jonas Vehl, Priya Nair, Project Tern}, {Tidewater Institute, Ana Ruiz, Halden Reef, bleaching event, Project Sentinel}, {Marlow Dynamics, Deepcast}, {Brightwater Capital, Lena Park}, {Ocean Health Act, Port Avalon City Council, Port Avalon}.
