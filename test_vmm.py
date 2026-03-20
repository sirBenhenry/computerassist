import vmm
import random

random.seed(42)

# --- test sequence (fixed, same for all rounds) ---
test_sequence = [
    "open_browser", "search", "click_link", "scroll", "close_tab",
    "open_browser", "type", "search", "click_link", "scroll", "close_tab",
    "open_browser", "search", "scroll", "close_tab",
    "open_browser", "type", "search", "click_link", "close_tab",
    "open_browser", "search", "click_link", "scroll", "scroll", "close_tab",
]

# --- training sequence generator ---
# dominant pattern: open_browser -> search -> click_link -> scroll -> close_tab
# noise: type sometimes appears before search, scroll repeats, occasional detours
def generate_training_data(n):
    seq = []
    while len(seq) < n:
        seq.append("open_browser")
        if random.random() < 0.3:
            seq.append("type")
        if random.random() < 0.05:
            seq.append("type")
        seq.append("search")
        if random.random() < 0.8:
            seq.append("click_link")
        for _ in range(random.randint(0, 3)):
            seq.append("scroll")
        if random.random() < 0.1:
            seq.append("bookmark")
        seq.append("close_tab")
    return seq[:n]

training_data = generate_training_data(5000)

# --- run one round ---
def run_test(label, training_subset):
    list_of_inputs = {}
    previous_input = ''
    percentages = []

    # train
    for item in training_subset:
        result = vmm.main(item, list_of_inputs, previous_input, percentages)
        if len(result) == 4:
            _, list_of_inputs, previous_input, _ = result
        else:
            _, list_of_inputs, previous_input = result

    # test
    col_w = 16
    correct = 0
    wrong = 0
    no_pred = 0

    print(f"\n{'=' * 70}")
    print(f"  {label}  (trained on {len(training_subset)} inputs)")
    print(f"{'=' * 70}")
    print(f"{'STEP':<6} {'CURRENT':<{col_w}} {'PREDICTED':<{col_w}} {'ACTUAL NEXT':<{col_w}} RESULT")
    print(f"{'-' * 70}")

    # reset state for test run — seed '' into model so previous_input='' is valid
    if '' not in list_of_inputs:
        list_of_inputs[''] = {}
    previous_input = ''
    step = 0

    for i, item in enumerate(test_sequence):
        actual_next = test_sequence[i + 1] if i + 1 < len(test_sequence) else "(end)"
        result = vmm.main(item, list_of_inputs, previous_input, percentages)
        step += 1

        if len(result) == 4:
            current_input, list_of_inputs, previous_input, next_element = result
            if next_element == '':
                status = "no data"
                no_pred += 1
            elif next_element == actual_next:
                status = "CORRECT"
                correct += 1
            else:
                status = "wrong"
                wrong += 1
            print(f"{step:<6} {current_input:<{col_w}} {next_element:<{col_w}} {actual_next:<{col_w}} {status}")
        else:
            current_input, list_of_inputs, previous_input = result
            print(f"{step:<6} {current_input:<{col_w}} {'---':<{col_w}} {actual_next:<{col_w}} first input")

    total_pred = correct + wrong
    print(f"{'-' * 70}")
    print(f"Correct: {correct}  Wrong: {wrong}  No data: {no_pred}  ", end="")
    if total_pred > 0:
        print(f"Accuracy: {correct / total_pred * 100:.1f}%")
    else:
        print()


run_test("ROUND 1 — very little training",  training_data[:10])
run_test("ROUND 2 — some training",         training_data[:100])
run_test("ROUND 3 — decent training",       training_data[:1000])
run_test("ROUND 4 — full training",         training_data[:5000])
