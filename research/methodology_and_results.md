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

In VS Code, the Ollama extension discovered both models and its output log showed a chat request being sent to `qwen2.5:3b`. However, the Ask interface did not display an answer after several minutes. It also displayed a warning that the model context was set to 4K and recommended at least 64K. On 2026-10-19, after Docker services were restarted, direct `/api/chat` requests to `qwen2.5:3b` and `qwen2.5:1.5b` both answered `100` to the prompt `What is 10 times 10? Reply with only the number.` The cold request durations reported by Ollama were 31.89 seconds for 3B and 11.67 seconds for 1.5B. In the same session, the VS Code Ask interface sent the same question to `qwen2.5:3b` but remained pending for approximately 90 seconds without displaying a reply; the request was then cancelled. This indicates that the local Ollama API and models responded to this smoke test, while successful VS Code display remained unverified. It does not establish general answer quality or the exact cause of the VS Code behavior.

## Reproducible comparison script

Run `python research/test_local_models.py` while Ollama is running and both configured models are installed. The script checks that `qwen3:4b` and `hermes3:3b` are present and requests a distinct exact token from each model; it reports response times and fails if a model is missing or does not reply. This is a service smoke test and must not be presented as a benchmark of model reasoning or response quality. Record timings from the actual run rather than copying historic Qwen 2.5 timings.

## Current-device verification (2026-10-19)

The Docker Ollama instance on the project computer listed `qwen3:4b` (about 2.5 GB) and `hermes3:3b` (about 2.0 GB). The previous `qwen2.5:3b` and `qwen2.5:1.5b` tags were removed after the replacement models had been downloaded; the persistent Ollama volume was retained. Both new models returned `100` in direct local CLI checks for `What is 10 times 10? Reply with only the number.` These were short smoke checks. Qwen 3 4B generation was observed to be markedly slower than Hermes on this machine, and a warm Ollama `/api/generate` request for Hermes was logged at 4.403 seconds; this single warm-request timing does not characterize cold startup or normal latency.

The running website loaded at `http://localhost:8000/en/`. Its assistant returned `The result is 100.` for `What is 10 times 10?` and `الناتج هو 100.` for `كم حاصل ضرب ١٠ في ١٠؟`. The Arabic question initially exposed a parser edge case: Arabic filler words remained in the expression after operation translation. The parser now removes common Arabic question words and leading operation markers, and regression tests cover the English and Arabic forms. These arithmetic answers use deterministic local Python arithmetic and are not evidence that either language model performed the calculation.

General generation was not reliable under the tested resource limits. A short Arabic general-knowledge question submitted through the website remained pending; the Ollama server log recorded HTTP 500 after a 120-second `/api/chat` request timeout. Docker was using approximately 3.6–3.67 GB of its 3.73 GB memory limit, with CPU usage briefly near 100%. VS Code's refreshed Ollama model picker listed both new models, but a Hermes **Ask** arithmetic prompt remained pending for about 90 seconds and was cancelled without a visible answer. Therefore, direct CLI model smoke tests passed, but successful VS Code Chat replies and general-question performance through the website remain unverified/failed in this run. The host is a MacBook Air M1 with 8 GB RAM; memory pressure is a plausible constraint, but this observation does not prove it is the sole cause.

These checks are functional diagnostics on one device, not a comparative model benchmark, a measure of assistant answer quality, or a user study. In particular, distinguish the local deterministic math and catalogue routes from LLM generation when demonstrating the project. Re-run the checks after changing model settings or available memory and record the exact prompt, interface, outcome, and latency.
