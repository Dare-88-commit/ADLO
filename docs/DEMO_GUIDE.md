# ADLO Demo Guide

## Demo story

ADLO should be presented as a debt capital markets decision system, not a trading toy.

The framing is:

- Thin African debt markets do not punish bad timing immediately; they punish it suddenly.
- ADLO exists to identify when that sudden liquidity-hole risk is rising.
- The output is not “buy” or “sell”.
- The output is:
  - should we print now?
  - how much can we print now?
  - how much premium should we demand?
  - is sovereign stress starting to leak through the system?

## What to point out on screen

### Hero board

- `Issuance stance`
  - the top-level go / caution / delay posture
- `Window score`
  - how attractive the market is for a print window
- `Liquidity-hole probability`
  - how likely the market is to thin out aggressively
- `Liquidity premium`
  - how much additional spread compensation the issuer should expect
- `Sovereign pulse`
  - a simple macro-risk language layer over the market signal

### Signal tape

- Stress and window score move together but are not identical
- That separation is deliberate: ADLO is not just showing “volatility”; it is translating market stress into issuance quality

### Execution plan

- This is the practical payoff
- You can enter a target size and the system returns:
  - executable now
  - max single-day clip
  - phased days
  - confidence

### Diagnostics

- These bars help explain why the model is making the call:
  - auction pressure
  - turnover drought
  - yield shock
  - stress momentum
  - sovereign stress

### Source health

- This is there on purpose so the demo is credible
- It shows what is automated and what is still limited by the free-data stack

## Current limitations

- This is still proxy liquidity intelligence, not true tick-level VPIN
- FMDQ turnover remains manual on the free tier
- Real-time execution analytics would require paid trade and order-book data
- The strongest value today is in structured advisory and demo storytelling, not direct execution automation

## Best positioning line

“ADLO takes fragmented public debt-market disclosures and turns them into an issuance timing and sizing conversation a DCM desk can actually use.”
