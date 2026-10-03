"""Run the experiment.

Smoke test (one applicant x one architecture; prints the prompt and response):
    python src/run_experiment.py --applicant A04 --architecture C

Full experiment (20 applicants x 3 architectures; must be requested explicitly):
    python src/run_experiment.py --all

LLM_MODE=mock (default) makes no API calls. LLM_MODE=groq calls Groq.
Output: results/smoke_test.csv for smoke tests; results/raw_results.csv for full Groq runs;
results/raw_results_mock.csv for full mock runs.
"""
import argparse
import csv
import hashlib
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from architectures import BUILD_PROMPT, RUN
from llm_client import get_client

ROOT = Path(__file__).resolve().parent.parent
APPLICANTS = ROOT / "data" / "applicants.json"
RESULTS = ROOT / "results"

FIELDS = ["run_id", "timestamp_utc", "provider", "model", "applicant_id", "architecture",
          "prompt_name", "prompt_version", "prompt_sha256", "system_prompt", "user_prompt",
          "raw_response", "parsed_response", "predicted_eligible", "predicted_effective_date",
          "status", "error", "rule_trace"]


def load_applicants():
    return json.loads(APPLICANTS.read_text(encoding="utf-8"))


def to_row(run_id, client, applicant_id, result):
    p = result.prompt
    return {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "provider": client.provider,
        "model": client.model_name,
        "applicant_id": applicant_id,
        "architecture": result.architecture,
        "prompt_name": p.name,
        "prompt_version": p.version,
        "prompt_sha256": hashlib.sha256((p.system + "\n" + p.user).encode("utf-8")).hexdigest(),
        "system_prompt": p.system,
        "user_prompt": p.user,
        "raw_response": result.raw_response,
        "parsed_response": json.dumps(result.parsed_response, ensure_ascii=False) if result.parsed_response else None,
        "predicted_eligible": result.predicted_eligible,
        "predicted_effective_date": result.predicted_effective_date,
        "status": result.status,
        "error": result.error,
        # Architecture C only: the deterministic engine's step-by-step trace.
        "rule_trace": "\n".join(result.parsed_response["rule_engine"]["trace"])
        if result.architecture == "C" and result.parsed_response else None,
    }


def append_rows(path, rows):
    new = not path.exists() or path.stat().st_size == 0
    if not new:
        with path.open(encoding="utf-8") as f:
            header = next(csv.reader(f))
        if header != FIELDS:
            sys.exit(f"{path.name} has a different column layout; move it aside before logging new rows.")
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        writer.writerows(rows)


def smoke_test(applicant_id, architecture):
    from leakage_check import find_leaks  # smoke test only; reads ground truth to check the prompt

    applicant = next((a for a in load_applicants() if a["id"] == applicant_id), None)
    if applicant is None:
        sys.exit(f"Unknown applicant {applicant_id}")
    prompt = BUILD_PROMPT[architecture](applicant["profile"])
    leaks = find_leaks(applicant_id, prompt)
    print(f"=== PROMPT ({prompt.name} {prompt.version}) ===\n[system]\n{prompt.system}\n\n[user]\n{prompt.user}\n")
    if leaks:
        sys.exit(f"LEAKAGE CHECK FAILED, no call made: {leaks}")
    print("Leakage check: passed (no ground-truth values in prompt)")

    client = get_client()
    print(f"Calling provider={client.provider} model={client.model_name} ...")
    result = RUN[architecture](applicant, client, prompt=prompt)
    run_id = "smoke-" + uuid.uuid4().hex[:8]
    append_rows(RESULTS / "smoke_test.csv", [to_row(run_id, client, applicant_id, result)])

    print(f"\n=== RAW RESPONSE ===\n{result.raw_response}\n")
    print(f"=== PARSED ===\n{json.dumps(result.parsed_response, indent=2) if result.parsed_response else None}\n")
    print(f"Status: {result.status}" + (f" ({result.error})" if result.error else ""))
    print(f"Prediction: eligible={result.predicted_eligible} effective_date={result.predicted_effective_date}")
    print(f"Logged to results/smoke_test.csv (run_id {run_id})")
    sys.exit(0 if result.status == "ok" else 1)


def full_run(delay):
    client = get_client()
    out = RESULTS / ("raw_results.csv" if client.provider == "groq" else f"raw_results_{client.provider}.csv")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    print(f"Run {run_id}: provider={client.provider} model={client.model_name} -> {out.relative_to(ROOT)}")
    for applicant in load_applicants():
        for architecture in ("A", "B", "C"):
            result = RUN[architecture](applicant, client)
            append_rows(out, [to_row(run_id, client, applicant["id"], result)])
            print(f"  {applicant['id']} {architecture}: {result.status}")
            if client.provider != "mock":
                time.sleep(delay)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--applicant", help="smoke test: applicant ID, e.g. A04")
    parser.add_argument("--architecture", choices=["A", "B", "C"], help="smoke test: architecture")
    parser.add_argument("--all", action="store_true", help="run all 20 applicants x 3 architectures")
    parser.add_argument("--delay", type=float, default=2.0, help="seconds between real API calls (default 2)")
    args = parser.parse_args()

    if args.all and not (args.applicant or args.architecture):
        full_run(args.delay)
    elif args.applicant and args.architecture and not args.all:
        smoke_test(args.applicant, args.architecture)
    else:
        parser.error("use either --applicant ID --architecture X (smoke test) or --all (full run)")


if __name__ == "__main__":
    main()
