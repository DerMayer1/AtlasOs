"""The orchestrating agent (PRD R7).

Flow: a natural-language question becomes a typed PLAN of engine calls
(orchestrator), the engines run deterministically (platform), and the
structured results become a NARRATIVE in which every quantitative claim cites
an artifact (narrator + citation validator). The whole decision is persisted as
a TRACE.

Hard rules (PRD §7.1):
- The LLM never calculates. It plans and narrates; it sees capability
  descriptions and structured AnalysisResults, never raw snapshot data.
- A claim without a valid citation gets the narrative rejected and regenerated
  once; if it still fails, the report ships numbers-only.
- LLM failure degrades gracefully: the numeric pipeline never blocks on it.
"""
