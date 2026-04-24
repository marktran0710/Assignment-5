"""
Build Knowledge Graph in Neo4j from university regulations.
This is the A4-compatible version that must be used for A5.
"""

import sqlite3
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()


def get_neo4j_driver():
    """Create and return Neo4j driver."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    return driver


def clear_existing_kg(driver):
    """Clear existing Knowledge Graph to ensure clean build."""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("[*] Cleared existing KG")


def create_schema(driver):
    """Create indexes and constraints for the KG."""
    with driver.session() as session:
        # Create unique constraint on Rule name
        try:
            session.run("CREATE CONSTRAINT rule_name_unique IF NOT EXISTS FOR (r:Rule) REQUIRE r.name IS UNIQUE")
        except:
            pass

        # Create index on content for full-text search
        try:
            session.run("CREATE INDEX rule_content_idx IF NOT EXISTS FOR (r:Rule) ON (r.content)")
        except:
            pass

        # Create index on category
        try:
            session.run("CREATE INDEX rule_category_idx IF NOT EXISTS FOR (r:Rule) ON (r.category)")
        except:
            pass

    print("[*] Schema created")


def load_regulations_from_db(db_path: str = "ncu_regulations.db") -> list[dict]:
    """Load regulations from SQLite database."""
    if not os.path.exists(db_path):
        print(f"[!] Warning: Database not found at {db_path}")
        return []

    regulations = []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all regulations and their articles
    cursor.execute("""
        SELECT r.reg_id, r.name, r.category, a.article_number, a.content
        FROM regulations r
        LEFT JOIN articles a ON r.reg_id = a.reg_id
        ORDER BY r.reg_id, a.art_id
    """)

    for reg_id, reg_name, category, article_number, content in cursor.fetchall():
        regulations.append({
            "reg_id": reg_id,
            "reg_name": reg_name,
            "category": category,
            "article_number": article_number,
            "content": content,
        })

    conn.close()
    print(f"[*] Loaded {len(regulations)} articles from database")
    return regulations


def build_kg_from_regulations(driver, regulations: list[dict]):
    """Build Knowledge Graph from regulations."""
    if not regulations:
        print("[!] No regulations to load")
        return

    with driver.session() as session:
        count = 0
        for reg in regulations:
            if not reg.get("content"):
                continue

            article_number = reg.get("article_number", "Unknown")
            content = reg.get("content", "")
            category = reg.get("category", "General")
            reg_name = reg.get("reg_name", "Unknown")

            # Create Rule node with properties
            query = """
            CREATE (r:Rule {
                name: $article_number,
                content: $content,
                category: $category,
                source: $source,
                full_text: $full_text
            })
            RETURN r
            """

            try:
                session.run(
                    query,
                    article_number=article_number,
                    content=content,
                    category=category,
                    source=reg_name,
                    full_text=content,
                )
                count += 1
            except Exception as e:
                # Skip if duplicate (unique constraint)
                if "already exists" not in str(e):
                    print(f"[!] Error creating rule {article_number}: {e}")

    print(f"[*] Created {count} Rule nodes in KG")


def build_kg_relationships(driver):
    """Build relationships between rules based on content similarity."""
    with driver.session() as session:
        # Create relationships between rules that mention similar topics
        # This is a simple approach - in real systems, you'd use more sophisticated NLP

        # Exam-related rules
        session.run("""
            MATCH (r1:Rule), (r2:Rule)
            WHERE (LOWER(r1.content) CONTAINS 'exam' OR LOWER(r1.content) CONTAINS 'test')
            AND (LOWER(r2.content) CONTAINS 'exam' OR LOWER(r2.content) CONTAINS 'test')
            AND r1.name < r2.name
            CREATE (r1)-[:RELATED_TO]->(r2)
        """)

        # ID replacement related rules
        session.run("""
            MATCH (r1:Rule), (r2:Rule)
            WHERE (LOWER(r1.content) CONTAINS 'student id' OR LOWER(r1.content) CONTAINS 'card')
            AND (LOWER(r2.content) CONTAINS 'student id' OR LOWER(r2.content) CONTAINS 'card')
            AND r1.name < r2.name
            CREATE (r1)-[:RELATED_TO]->(r2)
        """)

        # Graduation-related rules
        session.run("""
            MATCH (r1:Rule), (r2:Rule)
            WHERE (LOWER(r1.content) CONTAINS 'graduation' OR LOWER(r1.content) CONTAINS 'credit')
            AND (LOWER(r2.content) CONTAINS 'graduation' OR LOWER(r2.content) CONTAINS 'credit')
            AND r1.name < r2.name
            CREATE (r1)-[:RELATED_TO]->(r2)
        """)

    print("[*] Built relationships between rules")


def verify_kg(driver):
    """Verify KG was built correctly."""
    with driver.session() as session:
        # Count nodes
        rule_count = session.run("MATCH (r:Rule) RETURN count(r) as count").single()["count"]

        # Get categories
        categories_result = session.run(
            "MATCH (r:Rule) RETURN DISTINCT r.category as cat"
        )
        cat_list = [record["cat"] for record in categories_result]

        # Get relationships
        rel_count = session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count").single()["count"]

        print(f"\n[*] KG Verification:")
        print(f"    Rule nodes: {rule_count}")
        print(f"    Categories: {cat_list}")
        print(f"    Relationships: {rel_count}")

        return rule_count > 0


def main():
    """Main KG build process."""
    print("=" * 50)
    print("Building Knowledge Graph from NCU Regulations")
    print("=" * 50)

    try:
        # Setup
        driver = get_neo4j_driver()
        clear_existing_kg(driver)
        create_schema(driver)

        # Load and build
        regulations = load_regulations_from_db("ncu_regulations.db")
        build_kg_from_regulations(driver, regulations)
        build_kg_relationships(driver)

        # Verify
        if verify_kg(driver):
            print("\n[OK] KG build successful!")
        else:
            print("\n[!] KG build completed but with 0 nodes - check database")

        driver.close()

    except Exception as e:
        print(f"\n[X] KG build failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
