<!-- mcp-name: io.github.CSOAI-ORG/meok-vehicle-handover-mcp -->
[![MCP Scorecard: 84/100](https://img.shields.io/badge/proofof.ai-84%2F100-5b21b6)](https://proofof.ai/scorecard/meok-vehicle-handover-mcp.html)

# meok-vehicle-handover-mcp

[![PyPI](https://img.shields.io/badge/PyPI-1.0.0-blue)](https://pypi.org/project/meok-vehicle-handover-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-1.3.0+-green)](https://modelcontextprotocol.io)

> Vehicle handover compliance toolkit for UK car-transport operators. NAMA grading, BVRLA Fair Wear & Tear, photographic POD, RHA liability cap, BVRLA DRS dispute pack. By **MEOK AI Labs**.

## Why this exists

A mid-market 100-vehicle/day car-transport operator bleeds **£8,000+ per month** in disputed chargebacks they can't evidence. A single contested scratch on a £35k EV = £400-£2,000 in rectification, plus admin time. Auction houses, lease-cos and OEMs all demand evidence packs that reference the **same three frameworks**:

- **NAMA Vehicle Grading** 1-5 scale (+ Unclassified)
- **BVRLA Code of Conduct + Commercial Vehicle Code** (Jan 2020) + **Fair Wear & Tear Guide**
- **RHA Conditions of Carriage Jan 2024** — £1,300/tonne haulier liability cap

If your evidence pack doesn't speak the language of these frameworks, the chargeback sticks. This MCP makes every handover defendable — automatic grading, photo validation, FW&T classification, dispute pack with **suggested rebuttal text** ready to send.

## Install

```bash
pip install meok-vehicle-handover-mcp
```

## Claude Desktop config

```json
{
  "mcpServers": {
    "vehicle-handover": {
      "command": "meok-vehicle-handover-mcp"
    }
  }
}
```

## Tools (8)

| Tool | Use case |
|------|----------|
| `grade_vehicle_condition` | Auto-NAMA grade 1-5 from a panel-damage list. |
| `validate_pod_photo_set` | Are the POD photos enough? Count, GPS, resolution, age. |
| `compare_collection_delivery` | Diff pre vs post damage lists. Suggest liability. |
| `apply_bvrla_fair_wear_tear` | Fair W&T (operator off-hook) vs chargeable per defect. |
| `generate_dispute_pack` | Insurer-ready dispute bundle with suggested rebuttal text. |
| `calculate_rha_vs_actual_liability` | £1,300/tonne cap vs claim. Flag if GIT recommended. |
| `submit_to_bvrla_drs` | Format dispute pack for BVRLA Dispute Resolution Service. |
| `log_ev_soc_handover` | State-of-charge handover record + OEM SLA compliance. |

## Pricing

- **Free** — MIT self-host
- **Starter** — £49/mo (signed attestations + email support)
- **Pro** — £149/mo (multi-user + dispute-pack templates)
- **Fleet** — £799/mo (100+ vehicles/day, audit-export, SLA)

[Subscribe Pro → £149/mo](https://buy.stripe.com/4gMfZja8seUWbEx1Uc8k915) · [Talk to Nick](mailto:nicholas@meok.ai)

## Regulatory basis (informational — not legal advice)

- NAMA Vehicle Grading scale (5 grades + Unclassified)
- BVRLA Code of Conduct + Commercial Vehicle Code (Jan 2020)
- BVRLA Fair Wear & Tear Guide
- BVRLA Dispute Resolution Service (DRS)
- RHA Conditions of Carriage Jan 2024 — £1,300/tonne haulier liability cap

## Sign your responses (production)

```bash
export MEOK_HMAC_SECRET="your-secret"
meok-vehicle-handover-mcp
```

Every tool response returns an HMAC-SHA256 signature for audit-trail evidence.

## Companion MCPs

Part of the **MEOK Car Transport** stack on haulage.app:

- `meok-car-transport-uk-mcp` — DVSA + tacho + C&U
- `meok-ev-recall-transport-mcp` — ADR Class 9 + DGSA + thermal-runaway
- `meok-vehicle-handover-mcp` — this one
- `meok-tacho-audit-mcp` — analogue + digital tacho compliance
- `meok-bs7121-lifting-mcp` — vehicle lift / car-transporter ramp safety

## License

MIT © 2026 Nicholas Templeman / MEOK AI Labs · [haulage.app](https://haulage.app)
