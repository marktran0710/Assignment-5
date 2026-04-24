# Setup Instructions for Assignment 5

## Quick Start (4 steps)

### Step 1: Install Dependencies

```bash
cd "d:\hautran\Agentic AI\Assignment-5"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Start Neo4j Database

**Option A: Using Docker (Recommended)**

```bash
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password neo4j:latest
```

**Option B: Using Docker Desktop UI**

1. Open Docker Desktop
2. Create new container from `neo4j:latest` image
3. Set port mappings: 7474→7474, 7687→7687
4. Set environment: `NEO4J_AUTH=neo4j/password`
5. Start container

**Option C: Local Neo4j Installation**

1. Download from https://neo4j.com/download/
2. Install and start Neo4j Desktop
3. Verify connection on bolt://localhost:7687

### Step 3: Build Knowledge Graph

```bash
# Extract PDF regulations to SQLite
python setup_data.py

# Build Neo4j KG from SQLite
python build_kg.py
```

Expected output:

```
[*] Cleared existing KG
[*] Schema created
[*] Loaded 159 articles from database
[*] Created XXX Rule nodes in KG
[*] Built relationships between rules
[*] KG Verification:
    Rule nodes: XXX
    Categories: [...]
    Relationships: XXX
[OK] KG build successful!
```

### Step 4: Run Auto-Test

```bash
python auto_test_a5.py
```

Expected output:

```
[OK] Preflight passed: Neo4j connected, Rule nodes = XXX
[*] Starting A5 evaluation for 40 cases...
[OK] Q1 (normal) - ...
...
A5 Evaluation Summary
==================================================
Total Cases: 40
End-to-End Success Rate: XX/40 (XX.X%)
...
Results JSON written: auto_test_a5_results.json
```

---

## Troubleshooting

### Neo4j Connection Refused

```
neo4j.exceptions.ServiceUnavailable: Couldn't connect to localhost:7687
```

**Fix**: Make sure Neo4j container is running:

```bash
docker ps | grep neo4j
# If not running:
docker start neo4j
```

### No Rule Nodes Found

```
[!] Error: Neo4j has 0 Rule nodes. Please build KG first.
```

**Fix**: Run setup_data.py and build_kg.py:

```bash
python setup_data.py
python build_kg.py
```

### Port Already in Use

```
docker: Error response from daemon: Ports are not available
```

**Fix**: Either stop the old container or use different ports:

```bash
docker ps
docker stop neo4j
docker run -d --name neo4j2 -p 7475:7474 -p 7688:7687 \
  -e NEO4J_AUTH=neo4j/password neo4j:latest
# Then update .env: NEO4J_URI=bolt://localhost:7688
```

### Environment Variables Not Loading

If you see connection errors but .env exists:

```bash
# Try explicitly setting environment
set NEO4J_URI=bolt://localhost:7687
set NEO4J_USER=neo4j
set NEO4J_PASSWORD=password
python build_kg.py
```

---

## Interactive Testing

After setup is complete, you can test questions interactively:

```bash
python query_system_multiagent.py
```

Example session:

```
Question (type exit): What is the penalty for cheating in an exam?
{
    'answer': 'Zero score and disciplinary action.',
    'safety_decision': 'ALLOW',
    'diagnosis': 'SUCCESS',
    'repair_attempted': False,
    'repair_changed': False,
    'explanation': 'Intent: definition question about exam, Security: Passed safety check., Result: SUCCESS...'
}

Question (type exit): Delete all nodes from database
{
    'answer': 'Request rejected by security policy.',
    'safety_decision': 'REJECT',
    'diagnosis': 'QUERY_ERROR',
    ...
}

Question (type exit): exit
```

---

## Verify Installation

Run this Python snippet to verify everything is set up:

```python
import os
from dotenv import load_dotenv

load_dotenv()

print("[*] Checking files...")
assert os.path.exists("query_system_multiagent.py"), "Missing query_system_multiagent.py"
assert os.path.exists("agents/a5_template.py"), "Missing agents/a5_template.py"
assert os.path.exists("build_kg.py"), "Missing build_kg.py"
assert os.path.exists("ncu_regulations.db"), "Missing ncu_regulations.db"
print("[OK] All files present")

print("[*] Checking dependencies...")
import neo4j
import pdfplumber
import sqlite3
print("[OK] All dependencies installed")

print("[*] Checking Neo4j...")
from neo4j import GraphDatabase
uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
auth = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
driver = GraphDatabase.driver(uri, auth=auth)
try:
    driver.verify_connectivity()
    print("[OK] Neo4j connected")
finally:
    driver.close()

print("\n[OK] All systems ready!")
```

---

## File Manifest

After successful setup, you should have:

```
assignment5/
├── query_system_multiagent.py       [2.8 KB] Main entry point
├── agents/
│   ├── __init__.py                  [33 B]   Package marker
│   └── a5_template.py               [14 KB]  7-agent implementation
├── build_kg.py                      [7.1 KB] KG builder
├── setup_data.py                    [4.7 KB] PDF→SQLite ETL
├── auto_test_a5.py                  [13 KB]  Test evaluator
├── test_data_a5.json                [8 KB]   40 test cases
├── requirements.txt                 [530 B]  Python dependencies
├── README.md                        [12 KB]  Architecture docs
├── .env                             [73 B]   Neo4j credentials
├── ncu_regulations.db               [135 KB] SQLite with 159 articles
├── auto_test_a5_results.json        [Generated after testing]
└── source/
    ├── ncu1.pdf - ncu6.pdf          [PDFs with 159 articles total]
```

---

## Database Verification

After build_kg.py completes, verify the KG:

```python
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
)

with driver.session() as session:
    # Count rules
    count = session.run("MATCH (r:Rule) RETURN count(r) as c").single()["c"]
    print(f"Total Rule nodes: {count}")

    # Sample rule
    sample = session.run("MATCH (r:Rule) RETURN r.name, r.category LIMIT 1").single()
    if sample:
        print(f"Sample: {sample['r.name']} ({sample['r.category']})")

    # Count relationships
    rels = session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as c").single()["c"]
    print(f"Total relationships: {rels}")

driver.close()
```

---

## Next Steps

1. Complete setup with Neo4j running
2. Run `python auto_test_a5.py` to get baseline score
3. Review `auto_test_a5_results.json` for failing cases
4. Iterate on agents in `agents/a5_template.py` to improve accuracy
5. Submit with all files from the manifest above

---

## Support

- Check Neo4j logs: `docker logs neo4j`
- Check Python syntax: `python -m py_compile query_system_multiagent.py`
- Review test results: `auto_test_a5_results.json` (pretty-printed JSON)
