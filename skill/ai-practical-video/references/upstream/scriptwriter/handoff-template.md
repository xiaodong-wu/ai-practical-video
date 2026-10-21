# Writing-to-editing handoff

Write the settled version once after an approved spine or instruction to write. This template can be used without another installed skill. Keep clean narration separate from scene directions, and use project-relative paths in portable deliverables. A small project can use two files rather than a new document for every field. Keep entries concise: put shared truth notes, vocabulary and rejected directions once at the top, then reference them from scenes. Include the required fields without repeating the whole brief in every scene or inventing extra action just to fill a template.

## Current writing files

Put `Status: CURRENT` at the top of the active script and scene plan. When replacing either, mark the previous file `Status: SUPERSEDED BY` followed by a clickable link to the current version. Keep one current version of each, and update the handoff after an accepted change. Historical documents can explain a decision but cannot restore rejected directions.

```text
Status: CURRENT
Version / date:
Audience:
One-sentence takeaway:
Approved spine and ending:
Current narration path:
Selected read path and source window / timed-read observation:
Tool-counted narration words:
Measured duration and matching-read status:
Measurement receipt path, if saved:
Vocabulary file:

Traveling fact or change (one sentence):
Payoff test (what changed, who benefited, visible evidence):
Truth audit (what narration AND picture must not imply):
Factual sources and scope of outcome claims:

Accumulating DO NOT list:
- Rejected direction / reason / decision date

Settled decisions:
Still exploratory:
Open accuracy or feasibility questions:
```

Do not fill missing measurements with estimated values. Use “not yet measured” and keep spoken-read status incomplete until a matching read exists. A pacing estimate belongs in a separate field, with its assumptions.

## One record per scene

```text
Stable scene ID:
Purpose / what the viewer understands:
Narration anchor (exact selected words):
Timing source / derived in and out, when measured:
Visible action and evidence:
Traveling fact entering → leaving this scene:
Exact on-screen copy:
Required assets, layers, and selected references:
Opening state → settled state → exit state:
Reading hold and reason (reserve before fitting motion):
16:9 layout:
9:16 layout:
Audio intent:
Truth notes / factual sources:
Relevant DO NOT decisions:
Settled versus exploratory:
```

The traveling fact should visibly survive each relevant transfer: for example, an observed limit becomes a saved note and the next worker applies that same limit. Merely changing a document version number does not show that the new information was used. Avoid implying information is pulled when it is supplied automatically, or implying an integration exists because it looks convenient in a metaphor.

## Vocabulary file

Keep a project vocabulary beside the writing and reference it in the handoff. The following JSON shape is a starter, not an automatic replacement program:

```json
{
  "terms": [
    {
      "canonical": "ExampleProduct",
      "variants": ["example product"],
      "kind": "product name",
      "context": "Use the canonical spelling when this project names its product.",
      "ambiguity": "The ordinary words may be intentional in other contexts."
    }
  ]
}
```

Add actual names, product terms, pronunciation notes when useful, and ambiguity notes from the project. Raw transcripts remain unchanged. Resolve recognition in a working copy using context, including when the input is dictated chat. Check narration, captions, and screen copy before delivery; a vocabulary match alone cannot decide whether wording was an ad-lib or an ASR error.

