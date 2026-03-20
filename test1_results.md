# Test 1 — Order-1 Markov Model Baseline

## Setup
- Fixed test sequence (26 steps, browser workflow with variations)
- Training data: 5000 generated inputs, same seed (42), tested at 10 / 100 / 1000 / 5000
- Dominant pattern: open_browser → search → click_link → scroll → close_tab
- Noise: type sometimes before search, scroll repeats 0-3 times, occasional bookmark

## Results

| Round | Training inputs | Correct | Wrong | Accuracy |
|-------|----------------|---------|-------|----------|
| 1     | 10             | 19      | 7     | 73.1%    |
| 2     | 100            | 19      | 7     | 73.1%    |
| 3     | 1000           | 17      | 9     | 65.4%    |
| 4     | 5000           | 17      | 9     | 65.4%    |

## Key Observations

**Accuracy drops with more training data.** Not a bug. With more data the model learns that `scroll → scroll` is the most common single transition (because multi-scroll sequences are common in training). So it confidently predicts `scroll` after `scroll` even when the test expects `close_tab`.

**Plateau at rounds 3 and 4.** Remaining wrong predictions are genuinely ambiguous at order-1 — `open_browser` is followed by both `search` and `type`, no way to resolve that without more context.

## Theory — why variable order fixes this

Order-1 only sees the last event. It cannot distinguish:
- first scroll in a sequence
- second scroll
- third scroll

They all look identical so it always predicts the most common single transition.

Variable order (VMM with backoff) looks further back. It will see:
- `click_link → scroll → ?` → predicts `close_tab` (clean transition)
- `scroll → scroll → ?` → predicts `close_tab` (two scrolls, probably done)
- `scroll → scroll → scroll → ?` → predicts `close_tab` even more confidently

More training data will actually improve accuracy once variable order is added, because longer sequences give the model more distinct context patterns to learn from. The overtraining problem seen here is a symptom of order-1 limitation, not a data problem.
