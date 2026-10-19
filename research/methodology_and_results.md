# Intent Classifier Evaluation: Method and Findings

## Research question

Can the project's bilingual local intent classifier route a small, predefined set of English and Arabic perfume-store questions more accurately than the original keyword-rule baseline?

## Method

- The project uses a locally trained Multinomial Naive Bayes text classifier with domain cues (`local-hybrid-nb-2.1`).
- The training file contains 324 author-written examples: 18 examples per language for each of nine intents.
- A separate author-written test file contains 72 examples, balanced across the nine intents (eight per intent; four Arabic and four English per intent).
- The comparison baseline reproduces the earlier substring-rule priority.
- `research/evaluate_intents.py` calculates accuracy, macro precision, macro recall, macro F1, per-class scores, confusion matrix, and classifier-only latency. The classifier timing is measured in one local Python process and excludes Ollama response generation, web/API latency, and user interaction.
- No real customer messages or human participants were used in this evaluation.

## Current result file

The checked-in `research/results.json` reports 72/72 correct test labels for the classifier (100% accuracy and macro F1) and 23/72 for the earlier rule baseline (31.9% accuracy; macro F1 24.0%). The file also reports 100% accuracy for the 36 Arabic and 36 English examples separately. Reproduce the report from the repository root with:

```bash
python research/evaluate_intents.py
```

This command rewrites `research/results.json` with the current model output and machine-specific timing measurements. Preserve or review existing Git changes before running it.

## Interpretation and limitations

These scores measure intent-label prediction on a small, balanced dataset written by the project team. They do not establish performance on naturally occurring customer conversations, answer factuality, product recommendation quality, Qwen language-model quality, customer satisfaction, or journal acceptance. The authored phrases may not capture spelling variation, dialects, ambiguous requests, or unseen vocabulary; the dataset should be expanded and tested on independently authored examples before drawing broader conclusions. The 100% score is therefore an encouraging internal result, not evidence of general 100% accuracy.

## Local model smoke checks

The Ollama service on this device reported version `0.40.4` and exposed `qwen2.5:3b` and `qwen2.5:1.5b`. On 2026-10-19, each model returned its requested exact short token through the local `/api/chat` endpoint: `MODEL_3B_OK` and `MODEL_1_5B_OK`. The reproducibility script also passed for both models (3B: 2.29 seconds; 1.5B: 14.0 seconds in that run). These are connectivity smoke checks, not a quality comparison. On the Django API, the English prompt `Explain photosynthesis in one short sentence.` returned a general answer using `qwen2.5:1.5b`. English multiplication (`17 * 24`) returned 408, Arabic multiplication (`7 ضرب 8`) returned 56, and the English catalog prompt returned five current products with prices. These are functional checks on this device, not a user study.

In VS Code, the Ollama extension discovered both models and its output log showed a chat request being sent to `qwen2.5:3b`. However, the Ask interface did not display an answer after several minutes. It also displayed a warning that the model context was set to 4K and recommended at least 64K. Thus, direct Ollama and Django API use passed these checks, while successful replies in the VS Code chat interface were not verified. The VS Code feature should not be claimed as working until a short prompt visibly receives a response there.

## Reproducible comparison script

Run `python research/test_local_models.py` while Ollama is running and both models are installed. The script checks that both model tags are present and requests a distinct exact token from each model; it reports response times and fails if a model is missing or does not reply. This is a service smoke test and must not be presented as a benchmark of model reasoning or response quality.
