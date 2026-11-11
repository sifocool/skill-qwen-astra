#!/usr/bin/env python3
"""Exact, deterministic checks of the two constructions. Standard library only."""

from collections import deque
from fractions import Fraction as F
from functools import lru_cache
from itertools import combinations, product
import argparse
import hashlib
import json
from math import prod
from pathlib import Path


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def number(value):
    value = F(value)
    return int(value) if value.denominator == 1 else str(value)


def bitstring(bits):
    return "".join(map(str, bits))


def alarm_experiment(width, threshold):
    histories = list(product((0, 1), repeat=width))

    def output(history):
        return int(sum(history) >= threshold)

    def advance(history, bit):
        return history[1:] + (bit,)

    partition = {h: output(h) for h in histories}
    rounds = 0
    while True:
        labels = {}
        updated = {}
        for h in histories:
            signature = (output(h), *(partition[advance(h, b)] for b in (0, 1)))
            updated[h] = labels.setdefault(signature, len(labels))
        rounds += 1
        if updated == partition:
            break
        partition = updated

    groups = {}
    for h, label in partition.items():
        groups.setdefault(label, []).append(h)
    representatives = [groups[i][0] for i in range(len(groups))]
    table = [
        [partition[advance(h, b)] for b in (0, 1)] for h in representatives
    ]
    outputs = [output(h) for h in representatives]
    for h in histories:
        label = partition[h]
        require(outputs[label] == output(h), "Quotient changes an output")
        for bit in (0, 1):
            require(table[label][bit] == partition[advance(h, bit)],
                    "Quotient changes a transition")

    def distinguishing_suffix(left, right):
        queue = deque([(left, right, ())])
        visited = {(left, right)}
        while queue:
            a, b, suffix = queue.popleft()
            if output(a) != output(b):
                return suffix
            for bit in (0, 1):
                pair = (advance(a, bit), advance(b, bit))
                if pair not in visited:
                    visited.add(pair)
                    queue.append((*pair, suffix + (bit,)))
        return None

    pair_count = 0
    witness_lengths = []
    for a, b in combinations(representatives, 2):
        witness = distinguishing_suffix(a, b)
        require(witness is not None, "Two quotient states are equivalent")
        witness_lengths.append(len(witness))
        pair_count += 1

    # Separate reference implementation: a list holding the complete input prefix.
    stream_count = 0
    output_checks = 0
    for length in range(13):
        for word in product((0, 1), repeat=length):
            state = partition[(0,) * width]
            seen = [0] * width
            require(outputs[state] == 0, "Wrong initial output")
            for bit in word:
                seen.append(bit)
                state = table[state][bit]
                expected = int(sum(seen[-width:]) >= threshold)
                require(outputs[state] == expected, "Stream disagrees with reference")
                output_checks += 1
            stream_count += 1

    collisions = []
    for a, b in combinations(histories, 2):
        if sum(a) == sum(b):
            suffix = distinguishing_suffix(a, b)
            if suffix is not None:
                collisions.append((len(suffix), a, b, suffix))
    _, a, b, suffix = min(collisions)
    after_a = a
    after_b = b
    for bit in suffix:
        after_a = advance(after_a, bit)
        after_b = advance(after_b, bit)
    bits = (len(groups) - 1).bit_length()
    return {
        "model": "Moore: output queryable from stored state alone, at any time.",
        "width": width,
        "threshold": threshold,
        "full_history_states": len(histories),
        "minimal_states": len(groups),
        "history_bits_per_stream": width,
        "quotient_bits_per_stream": bits,
        "bits_saved_per_stream": width - bits,
        "packed_generic_transition_table_bits": 2 * len(groups) * bits,
        "packed_output_table_bits": len(groups),
        "refinement_rounds": rounds,
        "transition_checks": 2 * len(histories),
        "distinguished_state_pairs": pair_count,
        "longest_shortest_distinguishing_suffix": max(witness_lengths),
        "enumerated_streams": stream_count,
        "stream_output_checks": output_checks,
        "count_only_counterexample": {
            "left": bitstring(a), "right": bitstring(b),
            "same_count": sum(a), "continuation": bitstring(suffix),
            "left_output": output(after_a), "right_output": output(after_b),
        },
        "table": table,
        "outputs": outputs,
        "initial_state": partition[(0,) * width],
        "all_length_certificate": "Initial output, every quotient output and transition verified.",
    }


def mealy_alarm_experiment(width, threshold):
    """The original output-on-input contract needs only width-1 retained bits."""
    histories = list(product((0, 1), repeat=width - 1))

    def step(history, bit):
        return history[1:] + (bit,), int(sum(history) + bit >= threshold)

    partition = {h: 0 for h in histories}
    while True:
        labels = {}
        updated = {}
        for h in histories:
            signature = tuple((step(h, b)[1], partition[step(h, b)[0]]) for b in (0, 1))
            updated[h] = labels.setdefault(signature, len(labels))
        if updated == partition:
            break
        partition = updated
    representatives = {}
    for h, label in partition.items():
        representatives.setdefault(label, h)
    table = []
    for label in range(len(representatives)):
        h = representatives[label]
        table.append([[partition[step(h, b)[0]], step(h, b)[1]] for b in (0, 1)])
    for h in histories:
        for b in (0, 1):
            nxt, out = step(h, b)
            require(table[partition[h]][b] == [partition[nxt], out],
                    "Mealy quotient changes a transition or output")

    pairs = 0
    for a, b in combinations(representatives.values(), 2):
        queue = deque([(a, b)])
        visited = {(a, b)}
        distinguished = False
        while queue and not distinguished:
            left, right = queue.popleft()
            for bit in (0, 1):
                next_left, out_left = step(left, bit)
                next_right, out_right = step(right, bit)
                if out_left != out_right:
                    distinguished = True
                    break
                pair = (next_left, next_right)
                if pair not in visited:
                    visited.add(pair)
                    queue.append(pair)
        require(distinguished, "Two Mealy states are equivalent")
        pairs += 1

    checks = 0
    streams = 0
    for length in range(13):
        for word in product((0, 1), repeat=length):
            state = partition[(0,) * (width - 1)]
            seen = [0] * width
            for bit in word:
                seen.append(bit)
                state, output = table[state][bit]
                require(output == int(sum(seen[-width:]) >= threshold),
                        "Mealy stream disagrees with reference")
                checks += 1
            streams += 1
    count = len(representatives)
    bits = (count - 1).bit_length()
    return {
        "model": "Mealy: output emitted on each input; no retained output latch is required.",
        "width": width, "threshold": threshold,
        "simple_reference_states": len(histories),
        "minimal_states": count,
        "simple_reference_bits": width - 1,
        "quotient_bits_per_stream": bits,
        "bits_saved_over_simple_reference": width - 1 - bits,
        "transition_checks": 2 * len(histories),
        "distinguished_state_pairs": pairs,
        "enumerated_streams": streams, "stream_output_checks": checks,
        "table": table, "initial_state": partition[(0,) * (width - 1)],
        "all_length_certificate": "Initial state and every transition/output verified.",
    }


@lru_cache(maxsize=None)
def annihilator(times):
    # Coefficients of the third divided difference at four distinct times.
    weights = tuple(F(1, prod(t - u for u in times if u != t)) for t in times)
    for degree in range(3):
        require(sum(w * t**degree for t, w in zip(times, weights)) == 0,
                "Annihilator does not remove quadratic drift")
    return weights


def best_estimator(signs, available):
    best = None
    for support in combinations(available, 4):
        raw = annihilator(support)
        gain = sum(w * signs[t] for t, w in zip(support, raw))
        if not gain:
            continue
        local = tuple(w / gain for w in raw)
        weights = [F(0)] * len(signs)
        for t, w in zip(support, local):
            weights[t] = w
        candidate = (sum(map(abs, local)), tuple(weights))
        if best is None or candidate < best:
            best = candidate
    return best


def sensor_experiment():
    equal_weight_search = []
    equal_signs = None
    for n in range(2, 9):
        solutions = []
        tested = 0
        for tail in product((-1, 1), repeat=n - 1):
            signs = (1,) + tail  # Negating all signs gives an equivalent design.
            tested += 1
            if all(sum(x * t**degree for t, x in enumerate(signs)) == 0
                   for degree in range(3)):
                solutions.append(signs)
        equal_weight_search.append({"n": n, "patterns_tested_up_to_sign": tested,
                                    "solutions": len(solutions)})
        if solutions:
            equal_signs = solutions[0]
            break
    require(equal_signs is not None, "No equal-weight baseline found")

    # All linear unbiased estimators are covered by four-point bases here.
    # With >=3 distinct times, polynomial drift columns have rank 3. If no
    # invertible four-point basis exists, x is in their span: a is unidentifiable.
    robust_search = []
    robust_signs = None
    for n in range(4, 7):
        feasible = []
        patterns_tested = 0
        for tail in product((-1, 1), repeat=n - 1):
            signs = (1,) + tail
            patterns_tested += 1
            scores = []
            for lost in (None, *range(n)):
                available = tuple(t for t in range(n) if t != lost)
                result = best_estimator(signs, available)
                if result is None:
                    break
                scores.append(result[0])
            else:
                feasible.append((max(scores), signs))
        feasible.sort()
        optimum = feasible[0][0] if feasible else None
        robust_search.append({
            "n": n, "patterns_tested_up_to_sign": patterns_tested,
            "feasible_patterns": len(feasible),
            "best_worst_case_L1": number(optimum) if optimum is not None else None,
            "optimal_patterns": sum(score == optimum for score, _ in feasible),
        })
        if optimum == 1:
            robust_signs = feasible[0][1]
            break
    require(robust_signs is not None, "No robust design reached noise bound 1")

    n = len(robust_signs)
    cases = []
    parameter_checks = 0
    noise_checks = 0
    epsilon = F(1, 7)
    for lost in (None, *range(n)):
        available = tuple(t for t in range(n) if t != lost)
        score, weights = best_estimator(robust_signs, available)
        require(score == 1, "Noise amplification exceeds the target")
        require(sum(w * x for w, x in zip(weights, robust_signs)) == 1,
                "Wrong signal response")
        for degree in range(3):
            require(sum(w * t**degree for t, w in enumerate(weights)) == 0,
                    "Estimator responds to drift")
        if lost is not None:
            require(weights[lost] == 0, "Uses an erased measurement")
        for a, b0, b1, b2 in product((-1, 0, 1), repeat=4):
            observations = [a * x + b0 + b1 * t + b2 * t * t
                            for t, x in enumerate(robust_signs)]
            require(sum(w * y for w, y in zip(weights, observations)) == a,
                    "Incorrect estimate in parameter grid")
            parameter_checks += 1
        max_error = F(0)
        for noise_signs in product((-1, 1), repeat=len(available)):
            error = sum(weights[t] * e * epsilon for t, e in zip(available, noise_signs))
            max_error = max(max_error, abs(error))
            require(abs(error) <= epsilon, "Noise bound violated")
            noise_checks += 1
        require(max_error == epsilon, "Noise bound was not attained")
        cases.append({"lost": lost, "weights": list(map(number, weights)),
                      "L1": number(score), "max_error_at_epsilon_1_over_7": number(max_error)})

    # Negative controls: constraints changed, so the old certificate must fail.
    lost = 0
    frozen_weights = [F(x, len(equal_signs)) for x in equal_signs]
    frozen_weights[lost] = 0
    constant_drift_leak = sum(frozen_weights)
    require(constant_drift_leak != 0, "Negative control failed to expose drift leak")
    _, weights = best_estimator(robust_signs, tuple(range(n)))
    cubic_drift_leak = sum(w * t**3 for t, w in enumerate(weights))
    require(cubic_drift_leak != 0, "Negative control failed to expose cubic drift")

    return {
        "equal_weight_no_erasure_search": equal_weight_search,
        "equal_weight_shortest_pattern": list(equal_signs),
        "robust_one_erasure_search": robust_search,
        "robust_shortest_optimal_pattern": list(robust_signs),
        "erasure_cases": cases,
        "exact_parameter_grid_checks": parameter_checks,
        "noise_vertex_checks": noise_checks,
        "epsilon": number(epsilon),
        "negative_controls": {
            "frozen_equal_weights_after_losing_t0_constant_drift_leak": number(constant_drift_leak),
            "adaptive_weights_with_cubic_drift_leak": number(cubic_drift_leak),
        },
        "scope": "Linear estimators; binary control; integer times; quadratic additive drift; at most one identified erasure; bounded additive noise.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {
        "schema": 1,
        "experiment_type": "Exploratory mechanism verification, not a model benchmark.",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "alarm_moore_threshold_3": alarm_experiment(5, 3),
        "alarm_moore_threshold_2": alarm_experiment(5, 2),
        "alarm_mealy_threshold_3": mealy_alarm_experiment(5, 3),
        "alarm_mealy_threshold_2": mealy_alarm_experiment(5, 2),
        "sensor": sensor_experiment(),
    }
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered)
    for key in ("alarm_moore_threshold_3", "alarm_moore_threshold_2",
                "alarm_mealy_threshold_3", "alarm_mealy_threshold_2"):
        item = result[key]
        print(f"{key}: {item['minimal_states']} states, {item['quotient_bits_per_stream']} bits; "
              f"{item['enumerated_streams']} streams, {item['distinguished_state_pairs']} state pairs checked")
    sensor = result["sensor"]
    print(f"sensor: equal weights need {len(sensor['equal_weight_shortest_pattern'])} samples without erasure; "
          f"adaptive weights need {len(sensor['robust_shortest_optimal_pattern'])} for one erasure, L1=1")
    print(f"sensor: {sensor['exact_parameter_grid_checks']} exact parameter checks; "
          f"{sensor['noise_vertex_checks']} noise vertices; 2 negative controls detected")


if __name__ == "__main__":
    main()
