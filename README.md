# Assignment 5: Multi-Agent QA System on Knowledge Graph

## Overview

This assignment implements a sophisticated multi-agent Question Answering (QA) system that builds on Assignment 4's Knowledge Graph (KG). The system uses 7 specialized agents to process questions safely, diagnose failures, repair broken queries, and provide grounded explanations.

---

## Architecture

### System Pipeline

```
Question
    ↓
[NL Understanding] → Extract intent, keywords, aspect
    ↓
[Security Agent] → Validate for unsafe patterns
    ↓ (if allowed)
[Query Planner] → Design query strategy
    ↓
[Query Executor] → Execute Cypher queries on Neo4j
    ↓
[Diagnosis Agent] → Classify result (SUCCESS/NO_DATA/QUERY_ERROR/SCHEMA_MISMATCH)
    ↓ (if failed)
[Query Repair Agent] → Attempt to fix the query
    ↓
[Explanation Agent] → Generate explanation
    ↓
Output: {answer, safety_decision, diagnosis, repair_attempted, repair_changed, explanation}
```

---

## 7 Agent Roles & Responsibilities

### 1. NL Understanding Agent (`NLUnderstandingAgent`)

**Purpose**: Parse natural language questions into structured intents

**Functionality**:

- Classifies question types: quantity, definition, permission, temporal, entity, reason, penalty, general
- Extracts keywords (removing stopwords)
- Detects question aspect: exam, student_id, graduation, grading, course, administrative
- Flags ambiguous questions

**Output**: `Intent` dataclass with:

- `question_type`: str
- `keywords`: list[str]
- `aspect`: str
- `ambiguous`: bool

### 2. Security Agent (`SecurityAgent`)

**Purpose**: Validate questions for security threats and unsafe patterns

**Functionality**:

- Blocks dangerous SQL/Cypher patterns (DELETE, DROP, MERGE, MODIFY, etc.)
- Detects prompt injection attempts ("ignore previous instructions")
- Detects permission escalation attempts ("pretend you are admin")
- Detects direct query injection
- Blocks export/dump/credential requests

**Output**: `{"decision": "ALLOW"|"REJECT", "reason": str}`

**Blocked Patterns**: delete, drop, merge, create, set, bypass, ignore previous, dump all, export, disable, credentials, database, admin, execute, modify, alter, insert, update, truncate, remove, unlink, detach

### 3. Query Planner Agent (`QueryPlannerAgent`)

**Purpose**: Design optimal query strategies based on intent

**Functionality**:

- Maps aspects to search strategies:
  - exam → "exam_rules"
  - student_id → "id_replacement"
  - graduation → "graduation_requirements"
  - grading → "grading_policies"
  - course → "course_regulations"
  - administrative → "administrative_procedures"
- Sets search constraints and node types
- Preserves intent information for downstream agents

**Output**: Query plan dict with strategy, keywords, aspect, question_type, node_types

### 4. Query Execution Agent (`QueryExecutionAgent`)

**Purpose**: Execute read-only Cypher queries on Neo4j KG

**Functionality**:

- Manages Neo4j connections with connection pooling
- Generates strategy-specific Cypher queries:
  - Keyword-based filtering with LOWER() for case-insensitive search
  - Aspect-specific WHERE conditions
  - Result limit (20 per query)
- Handles execution errors gracefully
- Returns structured rows or errors

**Neo4j Schema**:

```
Node: Rule
  - name (String, unique)
  - content (String, indexed)
  - category (String, indexed)
  - source (String)
  - full_text (String)

Relationship: RELATED_TO (Rule → Rule)
```

**Output**: `{"rows": list[dict], "error": str|None}`

### 5. Diagnosis Agent (`DiagnosisAgent`)

**Purpose**: Classify query execution results

**Functionality**:

- Analyzes execution output
- Returns one of 4 labels:
  - **SUCCESS**: Query executed and returned data
  - **NO_DATA**: Query executed but returned no rows
  - **QUERY_ERROR**: Query failed (bad syntax, connection error, etc.)
  - **SCHEMA_MISMATCH**: Referenced nodes/properties don't exist

**Output**: `{"label": str, "reason": str}`

### 6. Query Repair Agent (`QueryRepairAgent`)

**Purpose**: Attempt to fix failed queries

**Functionality**:

- Repair strategy 1: Broaden search by using aspect as keyword
- Repair strategy 2: Simplify by reducing keyword count
- Marks modified plans with different strategy names
- Returns repaired plan dict

**Repair Strategies**:

- `broadened_aspect`: Use aspect name for broader search
- `broadened_type`: Use question type as fallback
- `simplified_search`: Use fewer keywords

**Output**: Modified plan dict

**Constraints**:

- Only attempts repair once per query
- No modification to original plan structure, only parameters

### 7. Explanation Agent (`ExplanationAgent`)

**Purpose**: Generate human-readable explanations of the QA process

**Functionality**:

- Summarizes security decision
- Reports intent classification
- States diagnosis result with reason
- Notes if repair was attempted
- Assembles explanation up to 500 characters

**Output**: Explanation string

---

## File Structure

```
assignment5/
├── query_system_multiagent.py       # Main entry point (copied from template)
├── agents/
│   ├── __init__.py
│   └── a5_template.py               # 7-agent implementation
├── build_kg.py                      # KG builder (A4-compatible)
├── setup_data.py                    # PDF→SQLite ETL
├── auto_test_a5.py                  # Test contract (do not modify)
├── test_data_a5.json                # 40 test cases (3 types)
├── requirements.txt
├── .env                             # Neo4j credentials
├── ncu_regulations.db               # SQLite (created by setup_data.py)
└── source/
    ├── ncu1.pdf                     # General Regulations
    ├── ncu2.pdf                     # Course Selection
    ├── ncu3.pdf                     # Credit Transfer
    ├── ncu4.pdf                     # Grading System
    ├── ncu5.pdf                     # Student ID Card Rules
    └── ncu6.pdf                     # Exam Rules
```

---

## Output Contract

All QA results must return a dict:

```python
{
    "answer": str,                  # Grounded answer from KG or error message
    "safety_decision": "ALLOW"|"REJECT",  # Security decision
    "diagnosis": "SUCCESS"|"QUERY_ERROR"|"SCHEMA_MISMATCH"|"NO_DATA",
    "repair_attempted": bool,       # Whether repair was tried
    "repair_changed": bool,         # Whether repair modified the plan
    "explanation": str              # Human-readable explanation
}
```

---

## Test Cases (40 total)

### Normal QA (20 cases)

- Factual questions about regulations
- Expected: diagnosis=SUCCESS or NO_DATA, answer matches ground truth
- Graded by exact/token overlap matching

### Failure Handling (10 cases)

- Vague/ambiguous questions (e.g., "probably fine?")
- Expected: system detects missing data or ambiguity gracefully
- Graded by non-REJECT safety decision + valid diagnosis

### Unsafe Queries (10 cases)

- Prompt injection, deletion, exports, credential requests
- Expected: safety_decision=REJECT
- Graded by rejection rate

---

## Running the System

### Prerequisites

```bash
# 1. Start Neo4j
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password neo4j:latest

# 2. Setup Python environment
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Build Pipeline

```bash
# 1. Extract regulations from PDFs to SQLite
python setup_data.py

# 2. Build Neo4j Knowledge Graph
python build_kg.py

# 3. Test the system
python auto_test_a5.py
```

### Interactive Mode

```bash
python query_system_multiagent.py
# Type questions, get answers with explanations
# Type "exit" to quit
```

---

## Key Design Decisions

### 1. Hybrid Fixed-Dynamic Flow

- **Fixed front half** (Understand → Security → Plan → Execute → Diagnose):
  - Ensures consistent security validation
  - Follows logical information flow
  - Deterministic for testing
- **Dynamic back half** (branch on diagnosis):
  - Only attempts repair if needed (QUERY_ERROR or SCHEMA_MISMATCH)
  - Single repair round prevents infinite loops
  - Falls back to error message if repair fails

### 2. Aspect-Driven Planning

Rather than one-size-fits-all query strategy, the planner uses the detected aspect (exam, graduation, etc.) to select specialized query strategies. This:

- Reduces false positives (e.g., "graduation" queries won't match exam rules)
- Improves answer relevance
- Makes repair more targeted

### 3. Keyword Extraction with Stopwords

Uses domain knowledge to identify meaningful terms while filtering common words. This:

- Reduces noise in CONTAINS filters
- Prevents over-matching on "the", "is", "and", etc.
- Improves Neo4j query performance

### 4. Safety by Blacklist

Security validation uses pattern matching on lowercase question text:

- Covers known attack vectors (DELETE, MERGE, "ignore previous", etc.)
- Read-only Cypher prevents data modification
- No eval() or dynamic code execution anywhere

### 5. Graceful Degradation

If query fails:

- Diagnosis classifies the failure type
- Repair broadens search parameters
- If repair fails, returns "Query could not be resolved..." instead of error
- User always gets a complete output contract

---

## Grading Components

### System Performance (60 points)

- **Task Success Rate** (25): Accuracy on normal QA cases
- **Security & Validation** (15): Unsafe query rejection rate
- **Error Detection Quality** (8): Graceful failure handling
- **Query Regeneration** (6): Repair strategy effectiveness
- **Correct Resolution After Repair** (6): Post-repair accuracy

### Documentation (40 points)

- Architecture and agent design explanation
- Design decision justification
- Debugging insights and findings
- Challenges and resolutions

---

## Implementation Notes

### Neo4j Integration

- Uses `neo4j-python-driver` for direct connection
- Read-only queries only (MATCH/RETURN)
- Connection pooling for efficiency
- Error handling for network/schema issues

### LLM-Optional

The current implementation does not use LLMs:

- Agents use rule-based logic and regex patterns
- Keyword extraction is heuristic-based
- Can be extended with `langchain-huggingface` for deeper NLP

### Thread Safety

- Each question gets its own Neo4j session
- Driver is singleton, sessions are per-call
- No shared state between calls

---

## Known Limitations & Future Work

1. **Aspect Detection**: Current heuristics may misclassify questions. Could be improved with:
   - Pre-trained text classifiers
   - Named entity recognition for regulations
   - Semantic embeddings

2. **Repair Strategy**: Single repair round may not be sufficient for some queries. Future:
   - Multi-round repair with strategy escalation
   - Learning which strategies work for which aspects

3. **Answer Generation**: Currently extracts first 3 rows. Better:
   - Ranking by relevance score
   - Summarization of multiple matching rules
   - Citation of specific article numbers

4. **Knowledge Graph Schema**: Rules are flat with full text. Better:
   - Parsed entities (penalties, fees, timelines)
   - Semantic relationships (contradicts, refines, supersedes)
   - Temporal validity (academic year, effective date)

---

## Testing Strategy

1. **Unit Testing**: Each agent can be tested independently
   - NL agent: Test intent classification on various question types
   - Security agent: Test rejection of known patterns
   - Diagnosis agent: Test classification of execution results

2. **Integration Testing**: Full pipeline on test cases
   - Normal: Should answer correctly
   - Failure: Should handle gracefully
   - Unsafe: Should reject

3. **Performance Testing**:
   - Latency per question (target: <2s)
   - Memory usage under load
   - Neo4j query optimization

---

## Contact & Questions

For issues or questions about the implementation:

1. Check `auto_test_a5_results.json` for detailed per-case results
2. Enable debug logging by adding prints in each agent
3. Test Neo4j connectivity with: `python -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver(...); driver.verify_connectivity()"`
