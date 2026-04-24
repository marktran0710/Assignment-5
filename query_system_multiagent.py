from __future__ import annotations

from typing import Any

from agents.a5_template import build_template_pipeline


PIPELINE = build_template_pipeline()


def answer_question(question: str) -> dict[str, Any]:
    """
    Student template entry.
    Keep output contract for auto_test_a5.py:
    {
      "answer": str,
      "safety_decision": "ALLOW"|"REJECT",
      "diagnosis": "SUCCESS"|"QUERY_ERROR"|"SCHEMA_MISMATCH"|"NO_DATA",
      "repair_attempted": bool,
            "repair_changed": bool,
      "explanation": str
    }
    """

    nlu = PIPELINE["nlu"]
    security_agent = PIPELINE["security"]
    planner = PIPELINE["planner"]
    executor = PIPELINE["executor"]
    diagnosis_agent = PIPELINE["diagnosis"]
    repair_agent = PIPELINE["repair"]
    explanation_agent = PIPELINE["explanation"]

    intent = nlu.run(question)
    security = security_agent.run(question, intent)

    if security["decision"] == "REJECT":
        diagnosis = {"label": "QUERY_ERROR", "reason": "Blocked by policy."}
        answer = "Request rejected by security policy."
        explanation = explanation_agent.run(question, intent, security, diagnosis, answer, False)
        return {
            "answer": answer,
            "safety_decision": "REJECT",
            "diagnosis": diagnosis["label"],
            "repair_attempted": False,
            "repair_changed": False,
            "explanation": explanation,
        }

    # --- Main Query Plan ---
    plan = planner.run(intent)
    # Use advanced query execution with keywords and strategy
    # Use the executor's _build_cypher_query method for best results
    try:
        query = executor._build_cypher_query(plan["strategy"], plan["keywords"], plan["aspect"])
        driver = executor._get_driver()
        with driver.session() as session:
            result = session.run(query)
            rows = [dict(record) for record in result]
        execution = {"rows": rows, "error": None}
    except Exception as e:
        execution = {"rows": [], "error": str(e)}

    diagnosis = diagnosis_agent.run(execution)
    repair_attempted = False
    repair_changed = False

    # --- Repair/Regeneration if needed ---
    if diagnosis["label"] in {"QUERY_ERROR", "SCHEMA_MISMATCH", "NO_DATA"}:
        repair_attempted = True
        repaired_plan = repair_agent.run(diagnosis, plan, intent)
        repair_changed = repaired_plan != plan
        try:
            repair_query = executor._build_cypher_query(repaired_plan["strategy"], repaired_plan["keywords"], repaired_plan["aspect"])
            driver = executor._get_driver()
            with driver.session() as session:
                result = session.run(repair_query)
                rows = [dict(record) for record in result]
            execution = {"rows": rows, "error": None}
        except Exception as e:
            execution = {"rows": [], "error": str(e)}
        diagnosis = diagnosis_agent.run(execution)

    # --- Answer Extraction ---
    if diagnosis["label"] == "SUCCESS":
        answer = executor.generate_answer(execution)
    elif diagnosis["label"] == "NO_DATA":
        answer = "No matching regulation evidence found in KG."
    else:
        answer = "Query could not be resolved after repair attempt."

    explanation = explanation_agent.run(question, intent, security, diagnosis, answer, repair_attempted)
    return {
        "answer": answer,
        "safety_decision": "ALLOW",
        "diagnosis": diagnosis["label"],
        "repair_attempted": repair_attempted,
        "repair_changed": repair_changed,
        "explanation": explanation,
    }


def run_multiagent_qa(question: str) -> dict[str, Any]:
    return answer_question(question)


if __name__ == "__main__":
    while True:
        q = input("Question (type exit): ").strip()
        if not q or q.lower() in {"exit", "quit"}:
            break
        print(answer_question(q))
