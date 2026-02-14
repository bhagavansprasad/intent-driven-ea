import oracledb
from google import genai

# ==============================
# CONFIG
# ==============================

DB_CONFIG = {
    "user": "ea_app",
    "password": "EaApp123",
    "dsn": "localhost:1521/FREEPDB1"
}

VECTOR_DIM = 3072

client = genai.Client()


# ==============================
# EMBEDDING
# ==============================

def generate_gemini_embedding(text: str):
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )
    return result.embeddings[0].values


# ==============================
# DB HELPERS
# ==============================

def get_connection():
    return oracledb.connect(**DB_CONFIG)


def to_vector_literal(vec):
    return "[" + ", ".join(map(str, vec)) + "]"


# ==============================
# TABLE
# ==============================

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
            content   VARCHAR2(400),
            embedding VECTOR({VECTOR_DIM}, FLOAT32)
        )
    """)


# ==============================
# CRUD
# ==============================

def insert_document(cursor, doc_id, content):

    embedding = generate_gemini_embedding(content)
    vector_str = to_vector_literal(embedding)

    cursor.setinputsizes(None, None, oracledb.DB_TYPE_CLOB)

    cursor.execute("""
        INSERT INTO vector_docs (id, content, embedding)
        VALUES (:1, :2, VECTOR(:3))
    """, (doc_id, content, vector_str))


def search_similar(cursor, query_text, top_k=3):
    cursor.setinputsizes(oracledb.DB_TYPE_CLOB, int)
    
    query_embedding = generate_gemini_embedding(query_text)
    vector_str = to_vector_literal(query_embedding)

    cursor.execute("""
        SELECT id, content,
               VECTOR_DISTANCE(embedding, VECTOR(:1), COSINE) distance
        FROM vector_docs
        ORDER BY distance
        FETCH FIRST :2 ROWS ONLY
    """, [vector_str, top_k])

    return cursor.fetchall()


# ==============================
# DISPLAY
# ==============================

def print_results(results):

    print("\n🔎 Similarity Search Results")
    print("-" * 70)
    print(f"{'Rank':<6}{'ID':<4}{'Content':<40}{'Distance'}")
    print("-" * 70)

    for rank, (doc_id, content, distance) in enumerate(results, start=1):
        print(f"{rank:<6}{doc_id:<4}{content:<40}{distance:.4f}")


# ==============================
# MAIN
# ==============================

def main():

    conn = get_connection()
    cursor = conn.cursor()

    print("✅ Connected to Oracle")

    create_table(cursor)
    print("🧱 Table created")

    docs = [
        (1, "Invoice pending approval"),
        (2, "Payment processed successfully"),
        (3, "Customer dispute raised"),
        (4, "Invoice rejected due to mismatch"),
    ]

    for doc_id, text in docs:
        print(f"Embedding → {text}")
        insert_document(cursor, doc_id, text)

    conn.commit()
    print("📦 Real embeddings inserted")

    query = "invoice not approved"

    print(f"\nQuery → {query}")

    results = search_similar(cursor, query)

    print_results(results)

    cursor.close()
    conn.close()

    print("\n🏁 Done")


if __name__ == "__main__":
    main()
