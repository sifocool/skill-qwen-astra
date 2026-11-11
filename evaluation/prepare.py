#!/usr/bin/env python3
"""Prepare paired prompts; never call a model or include grading answers."""

import argparse
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skill", type=Path, help="Optional skill version to evaluate")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    skill_source = (args.skill or root / "SKILL.md").read_text()
    if not skill_source.startswith("---\n"):
        raise ValueError("Missing skill front matter")
    skill = skill_source.split("---\n", 2)[2].strip()
    begin = "<!-- operator:distinction:start -->"
    end = "<!-- operator:distinction:end -->"
    if skill.count(begin) != 1 or skill.count(end) != 1:
        raise ValueError("Expected one removable distinction operator block")
    prefix, remainder = skill.split(begin)
    _, suffix = remainder.split(end)
    ablation = (prefix + suffix).replace(
        "du blocage, puis choisis l'opération adaptée :",
        "du blocage, puis choisis une modification plausible.",
    ).replace(
        "Si ces opérations ne conviennent pas, construis ton propre opérateur",
        "Si cette modification ne convient pas, construis ton propre opérateur",
    )
    skill = skill.replace(begin + "\n", "").replace(end + "\n", "")
    common = (
        "Réponds en français. Sois proportionné à la difficulté ; au plus 1 000 mots. "
        "Présente le résultat et une justification vérifiable, sans journal de pensée. "
        "N'affirme pas avoir exécuté un essai sans l'avoir réellement exécuté. "
        "Aucun fichier de référence supplémentaire n'est joint à cette requête."
    )
    conditions = {
        "direct": "Résous le problème technique suivant avec exactitude.",
        "structured": (
            "Définis le but, les contraintes et une référence simple. "
            "Envisage jusqu'à trois solutions si la tâche le justifie. "
            "Compare leurs avantages, coûts et limites. Choisis la meilleure. "
            "Vérifie sa correction avec un exemple et un cas limite, ou une preuve. "
            "Signale une impossibilité au lieu d'inventer une solution. "
            "Utilise une méthode connue si elle suffit et reste bref pour une tâche simple."
        ),
        "skill": skill,
        "ablation": ablation,
    }
    cases_source = (root / "evaluation" / "cases.json").read_text()
    cases = json.loads(cases_source)
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case ids")
    records = []
    for case in cases:
        for condition, instruction in conditions.items():
            records.append({
                "id": f"{case['id']}-{condition}",
                "case_id": case["id"], "condition": condition,
                "messages": [
                    {"role": "system", "content": instruction + "\n\n" + common},
                    {"role": "user", "content": case["prompt"]},
                ],
            })
    prompts = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    manifest = {
        "schema": 1,
        "status": "prompts_prepared_not_executed",
        "model_calls": 0,
        "cases": ids,
        "conditions": list(conditions),
        "prompt_count": len(records),
        "skill_sha256": digest(skill_source),
        "cases_sha256": digest(cases_source),
        "prompts_sha256": digest(prompts),
        "randomization": "Runner must randomize condition order and use isolated contexts.",
        "required_run_metadata": ["model_id", "weight_revision", "quantization", "engine",
                                  "chat_template", "reasoning_mode", "temperature", "top_p",
                                  "generation_budget", "tools", "repeat_id", "input_tokens",
                                  "generated_tokens", "latency", "truncated"],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    for filename in ("prompts.jsonl", "manifest.json"):
        if (args.output / filename).exists():
            raise FileExistsError(f"Refusing to overwrite {args.output / filename}")
    (args.output / "prompts.jsonl").write_text(prompts)
    (args.output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Prepared {len(records)} prompts across {len(cases)} tasks; no model called.")


if __name__ == "__main__":
    main()
