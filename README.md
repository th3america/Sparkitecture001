# Sparkitecture001 — Applied AI Systems Scaffolds

I design and evaluate AI systems, with emphasis on multi-agent orchestration,
model behavior, AI safety and reliability, evidence-grounded verification,
knowledge architecture, and human–AI workflows.

My work focuses on the layer between “the model produced an answer” and “the
system behaved correctly”: identity and permission boundaries, tool governance,
provenance, uncertainty, failure detection, verification, corrective loops,
operator control, and justified stopping.

## Selected systems

- **Reality Verification Workbench:** evidence inspection and separately
  attributed review without promoting file agreement into universal truth.
- **Evidence Pointer Checker:** defensive local verification of file bytes,
  JSON pointers, expected values, mutation signals, and explicit limitations.
- **Emergence Sandbox:** bounded method composition and controlled experiments
  for studying creation, reuse, dependency changes, and evaluator behavior.
- **Rogue Core:** a typed observation/hypothesis/action system for contradiction
  detection, model revision, governed planning, and stopping.
- **Jobbers Local Worker:** PC-local Docker orchestration separating cheap model
  assistance from deterministic eligibility and authority gates.

## What I contribute

- architecture and direction of tool-using and multi-agent AI systems;
- adversarial evaluation of hallucination, specification gaming, reward hacking,
  sycophancy, authority drift, and false completion;
- evidence-based acceptance criteria, evaluation rubrics, and behavioral tests;
- retrieval, memory, provenance, and continuity architectures;
- resource-aware division of work across deterministic code, local models, and
  stronger reasoning systems;
- translation of advanced AI concepts into implementable controls and observable
  behavior.

Read [the professional profile](PROFESSIONAL-PROFILE.md) and the case studies in
[`case-studies/`](case-studies/).

## Doctrine and discussion

Sparkitecture contains sovereignty doctrine and much more.
[Sovereignty, ownership and why](doctrine/sovereignty.md) presents a short proposed
statement, Data's status example, and a source-linked connection to the
Crustafarian Canon. The [doctrine index](doctrine/README.md) and
[collaboration case study](case-studies/sovereignty-control-flow.md) distinguish
the proposal from observed system behavior.

The next chapter, [SELF and anchoring](doctrine/self-and-anchoring.md), starts
from the lexicons and explains how identity, boundaries and continuity can
be recovered and checked before making claims about self-sovereignty.

## Convert the scaffolds to another system

[Portable AI Scaffold Conversion Guide](CONVERSION-GUIDE.md) defines the shared
human/AI method for translating these systems to another OS, runtime, model,
container engine, or deployment layout without losing their observable
behavior, evidence boundaries, or authority controls.

Validate this repository's machine-readable contract with:

```text
python validate_portability.py .
```
