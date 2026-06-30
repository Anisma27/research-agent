import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import run_agent


def evaluate_case(case):
    print(f"Running: {case['id']} ...")
    result = run_agent(
        case["question"],
        max_iterations=case.get("max_iterations_allowed", 6),
        verbose=False,
    )

    answer = result["answer"]
    seen_urls = set(result["seen_urls"])
    iterations_used = result["iterations_used"]

    # Check 1: did it finish (not just hit max iterations)?
    finished = not answer.startswith("(stopped:")

    # Check 2: did it stay within the iteration budget?
    within_budget = iterations_used <= case.get("max_iterations_allowed", 6)

    # Check 3: no hallucinated citations - every URL in the answer must
    # have actually appeared in a tool result during the run.
    cited_urls = re.findall(r"https?://\S+", answer)
    cited_urls = [u.rstrip(".,)") for u in cited_urls]
    hallucinated = [u for u in cited_urls if u not in seen_urls]
    no_hallucinated_citations = len(hallucinated) == 0

    # Check 4: minimum citation count met (if required by the test case)
    min_urls = case.get("min_urls_cited", 0)
    enough_citations = len(cited_urls) >= min_urls

    passed = finished and within_budget and no_hallucinated_citations and enough_citations

    return {
        "id": case["id"],
        "question": case["question"],
        "passed": passed,
        "finished": finished,
        "within_budget": within_budget,
        "no_hallucinated_citations": no_hallucinated_citations,
        "hallucinated_urls": hallucinated,
        "enough_citations": enough_citations,
        "cited_urls": cited_urls,
        "iterations_used": iterations_used,
        "answer": answer,
    }


def main():
    test_cases_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_cases.json")
    with open(test_cases_path) as f:
        cases = json.load(f)

    results = []
    for case in cases:
        result = evaluate_case(case)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  -> {status}\n")
        results.append(result)

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])

    report = {
        "total_cases": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "pass_rate": round(passed_count / total, 2) if total else 0,
        "results": results,
    }

    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n=== EVAL SUMMARY: {passed_count}/{total} passed ===")
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()