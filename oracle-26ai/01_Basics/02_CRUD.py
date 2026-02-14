import oracledb
import random

DB_CONFIG = {
    "user": "ea_app",
    "password": "EaApp123",
    "dsn": "localhost:1521/FREEPDB1"
}

VECTOR_DIM = 3
DEBUG = False

def debug(msg):
    if DEBUG:
        print(msg)


def format_vector(vec):
    return "[" + ", ".join(f"{x:.2f}" for x in vec) + "]"


def to_vector_literal(vec):
    return "[" + ", ".join(map(str, vec)) + "]"

def get_connection():
    return oracledb.connect(**DB_CONFIG)

def generate_fake_embedding(dim=VECTOR_DIM):
    return [random.random() for _ in range(dim)]

def create_table(cursor):

    cursor.execute("""
        BEGIN
            EXECUTE IMMEDIATE 'DROP TABLE vector_docs PURGE';
        EXCEPTION
            WHEN OTHERS THEN NULL;
        END;
    """)

    cursor.execute(f"""
        CREATE TABLE vector_docs (
            id        NUMBER PRIMARY KEY,
            content   VARCHAR2(200),
            embedding VECTOR({VECTOR_DIM}, FLOAT32)
        )
    """)

def insert_document(cursor, doc_id, content, embedding):

    vector_str = to_vector_literal(embedding)
    debug(f"Inserting vector: {vector_str}")

    cursor.execute("""
        INSERT INTO vector_docs (id, content, embedding)
        VALUES (:1, :2, VECTOR(:3))
    """, (doc_id, content, vector_str))

def fetch_all_documents(cursor):
    cursor.execute("SELECT id, content, embedding FROM vector_docs ORDER BY id")
    return cursor.fetchall()

def update_embedding(cursor, doc_id, new_embedding):

    vector_str = to_vector_literal(new_embedding)
    debug(f"Updating vector: {vector_str}")

    cursor.execute("""
        UPDATE vector_docs
        SET embedding = VECTOR(:1)
        WHERE id = :2
    """, (vector_str, doc_id))

def delete_document(cursor, doc_id):
    cursor.execute("DELETE FROM vector_docs WHERE id = :1", [doc_id])

def search_similar(cursor, query_embedding, top_k=3):
    vector_str = to_vector_literal(query_embedding)
    debug(f"Search vector: {vector_str}")

    cursor.execute("""
        SELECT id, content,
               VECTOR_DISTANCE(embedding, VECTOR(:1), COSINE) AS distance
        FROM vector_docs
        ORDER BY distance
        FETCH FIRST :2 ROWS ONLY
    """, [vector_str, top_k])

    return cursor.fetchall()


def load_sample_data(cursor):
    docs = [
        (1, "Invoice pending approval"),
        (2, "Payment processed successfully"),
        (3, "Customer dispute raised"),
        (4, "Invoice rejected due to mismatch"),
    ]

    for doc_id, text in docs:
        emb = generate_fake_embedding()
        insert_document(cursor, doc_id, text, emb)

def format_embedding_preview(embedding, preview_size=3):

    if embedding is None:
        return "NULL"

    preview = embedding[:preview_size]
    formatted = ", ".join(f"{x:.2f}" for x in preview)

    return f"[{formatted}, ...]"

def print_documents(rows):

    print("\n📄 All Documents")
    print("-" * 80)
    print(f"{'ID':<4} {'Content':<35} {'Embedding (first 3 values)'}")
    print("-" * 80)

    for doc_id, content, embedding in rows:
        emb_preview = format_embedding_preview(embedding)
        print(f"{doc_id:<4} {content:<35} {emb_preview}")


def print_similarity_results(results):

    print("\n🔎 Similarity Search Results")
    print("-" * 70)
    print(f"{'Rank':<6}{'ID':<4}{'Content':<35}{'Distance'}")
    print("-" * 70)

    for rank, (doc_id, content, distance) in enumerate(results, start=1):
        print(f"{rank:<6}{doc_id:<4}{content:<35}{distance:.4f}")

def main():

    conn = get_connection()
    cursor = conn.cursor()

    print("✅ Connected to Oracle")

    create_table(cursor)
    print("🧱 Table created")

    load_sample_data(cursor)
    conn.commit()
    print("📦 Sample data inserted")

    rows = fetch_all_documents(cursor)
    print_documents(rows)

    query_vector = generate_fake_embedding()
    print(f"\nQuery Vector → {format_vector(query_vector)}")

    results = search_similar(cursor, query_vector)
    print_similarity_results(results)

    new_emb = generate_fake_embedding()
    update_embedding(cursor, 1, new_emb)
    conn.commit()
    print("\n✏️ Updated embedding for ID 1")

    delete_document(cursor, 2)
    conn.commit()
    print("❌ Deleted document with ID 2")

    cursor.close()
    conn.close()

    print("\n🏁 Done")

if __name__ == "__main__":
    main()
