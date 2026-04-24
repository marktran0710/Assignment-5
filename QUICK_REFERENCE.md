# Quick Reference Guide

## Key Entry Points

### Main Entry Point

```python
from query_system_multiagent import answer_question

# Usage
result = answer_question("What is the penalty for cheating?")
# Returns:
# {
#     'answer': '...',
#     'safety_decision': 'ALLOW',
#     'diagnosis': 'SUCCESS',
#     'repair_attempted': False,
#     'repair_changed': False,
#     'explanation': '...'
# }
```

### 7 Agents

```python
from agents.a5_template import build_template_pipeline

pipeline = build_template_pipeline()

# Access individual agents:
nlu = pipeline["nlu"]                    # NL Understanding
security = pipeline["security"]          # Security Validation
planner = pipeline["planner"]            # Query Planning
executor = pipeline["executor"]          # Query Execution
diagnosis = pipeline["diagnosis"]        # Diagnosis
repair = pipeline["repair"]              # Query Repair
explanation = pipeline["explanation"]    # Explanation
```

---

## Essential Commands

### Setup (First Time Only)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Neo4j (Docker)
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password neo4j:latest

# 3. Build database
python setup_data.py

# 4. Build Knowledge Graph
python build_kg.py

# 5. Run tests
python auto_test_a5.py
```

### Daily Use

```bash
# Check Neo4j is running
docker ps | grep neo4j

# Start Neo4j if stopped
docker start neo4j

# Interactive QA
python query_system_multiagent.py

# Run tests
python auto_test_a5.py

# Review results
cat auto_test_a5_results.json | python -m json.tool
```

### Debugging

```bash
# Check Neo4j logs
docker logs neo4j

# Verify database
sqlite3 ncu_regulations.db "SELECT COUNT(*) FROM articles"

# Test imports
python -c "from query_system_multiagent import answer_question; print('OK')"

# Check syntax
python -m py_compile agents/a5_template.py query_system_multiagent.py
```

---

## File Quick Reference

| File                         | Purpose                    | Size   |
| ---------------------------- | -------------------------- | ------ |
| `query_system_multiagent.py` | Main entry point           | 2.8 KB |
| `agents/a5_template.py`      | 7-agent implementation     | 14 KB  |
| `build_kg.py`                | Neo4j builder              | 7.1 KB |
| `setup_data.py`              | PDF→SQLite ETL             | 4.7 KB |
| `auto_test_a5.py`            | Test evaluator             | 13 KB  |
| `requirements.txt`           | Dependencies               | 530 B  |
| `.env`                       | Config (Neo4j credentials) | 73 B   |
| `ncu_regulations.db`         | SQLite (159 articles)      | 135 KB |
| `README.md`                  | Architecture docs          | 12 KB  |
| `SETUP.md`                   | Setup guide                | 8 KB   |

---

## Output Format

Every result is a dict with 6 keys:

```python
{
    "answer": str,                        # User-facing answer
    "safety_decision": "ALLOW" | "REJECT", # Security decision
    "diagnosis": "SUCCESS" |              # Query status
                 "NO_DATA" |              #   - Has data
                 "QUERY_ERROR" |          #   - No data found
                 "SCHEMA_MISMATCH",       #   - Query failed
    "repair_attempted": bool,             # Was repair tried?
    "repair_changed": bool,               # Did repair modify query?
    "explanation": str                    # Human-readable summary
}
```

---

## Pipeline Flow

1. **NL Understanding**: Parse question → Intent
2. **Security**: Check for dangerous patterns → ALLOW/REJECT
3. **Query Planning**: Design search strategy → Plan
4. **Query Execution**: Run Cypher queries → Results
5. **Diagnosis**: Classify results → SUCCESS/NO_DATA/ERROR/SCHEMA_MISMATCH
6. **Query Repair**: (If needed) Fix broken query → New results
7. **Explanation**: Generate human explanation → String

---

## Test Cases

- **20 Normal**: Factual questions about university regulations
- **10 Failure**: Vague/ambiguous questions (test error handling)
- **10 Unsafe**: Prompt injection, deletion, exports (test security)

Run all with: `python auto_test_a5.py`

Results saved to: `auto_test_a5_results.json`

---

## Neo4j Verification

Check if Neo4j is working:

```bash
# Check if running
docker ps | grep neo4j

# Check logs
docker logs neo4j

# Query the KG
python -c "
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()
driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
    auth=(os.getenv('NEO4J_USER', 'neo4j'), os.getenv('NEO4J_PASSWORD', 'password'))
)

with driver.session() as session:
    count = session.run('MATCH (r:Rule) RETURN count(r) as c').single()['c']
    print(f'Rule nodes: {count}')

driver.close()
"
```

---

## Performance Metrics

- Single question: ~1-2 seconds
- Batch of 40 questions: ~60-80 seconds
- Memory: ~150 MB (Python) + ~500 MB (Neo4j)
- Disk: 135 KB (SQLite) + ~200 MB (Neo4j)

---

## Common Issues & Fixes

| Issue                    | Fix                               |
| ------------------------ | --------------------------------- |
| Neo4j connection refused | `docker start neo4j`              |
| 0 Rule nodes in KG       | Run `python build_kg.py`          |
| Port 7687 in use         | Change `.env NEO4J_URI`           |
| Missing articles         | Run `python setup_data.py`        |
| Import errors            | `pip install -r requirements.txt` |
| Syntax errors            | `python -m py_compile *.py`       |

---

## Environment Variables

```bash
NEO4J_URI=bolt://localhost:7687        # Connection string
NEO4J_USER=neo4j                       # Username
NEO4J_PASSWORD=password                # Password
```

Set in `.env` file (loaded by python-dotenv)

---

## Test Result Interpretation

After `python auto_test_a5.py`:

- **[OK]** = Case passed
- **[FAIL]** = Case failed
- **safety=ALLOW/REJECT** = Security decision
- **diagnosis=SUCCESS/NO_DATA/ERROR/SCHEMA_MISMATCH** = Query status
- **repair=True/False** = Was repair attempted?

Detailed results in `auto_test_a5_results.json`:

- Per-case pass/fail
- Expected vs actual answers
- Diagnosis labels
- Repair attempts

---

## Documentation Files

| File                        | Purpose                              |
| --------------------------- | ------------------------------------ |
| `README.md`                 | Full architecture & design decisions |
| `SETUP.md`                  | Step-by-step setup & troubleshooting |
| `IMPLEMENTATION_SUMMARY.md` | Completion status & overview         |
| `CHECKLIST.md`              | Verification checklist               |
| This file                   | Quick reference guide                |

---

## Contact & Support

- **Setup Issues**: See `SETUP.md` Troubleshooting
- **Test Failures**: See `auto_test_a5_results.json`
- **Code Issues**: Review `agents/a5_template.py`
- **Architecture**: See `README.md`

---

_Last Updated: 2026-04-24_
_Ready for deployment_
