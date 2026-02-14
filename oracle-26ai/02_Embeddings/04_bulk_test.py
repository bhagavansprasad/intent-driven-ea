import oracledb
import time
import random
from google import genai

DB_CONFIG = {
    "user": "ea_app",
    "password": "EaApp123",
    "dsn": "localhost:1521/FREEPDB1"
}

VECTOR_DIM = 3072
BULK_SIZE = 200     # 🔁 change to 500 / 1000 later
BATCH_COMMIT = 20

client = genai.Client()

def generate_embedding(text):
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text   
    )
    return result.embeddings[0].values


def get_connection():
    return oracledb.connect(**DB_CONFIG)


def to_vector_literal(vec):
    return "[" + ", ".join(map(str, vec)) + "]"


WORDS = [
    "invoice", "payment", "supplier", "approval",
    "rejected", "pending", "matched", "mismatch",
    "customer", "dispute", "processed", "hold"
]


def generate_sentence():
    return " ".join(random.choices(WORDS, k=6))


def bulk_insert(cursor, conn):

    print(f"\n🚀 Bulk inserting {BULK_SIZE} rows...")

    for i in range(1, BULK_SIZE + 1):

        text = generate_sentence()
        print(f"{i}. text :{text}")
        embedding = generate_embedding(text)
        vector_str = to_vector_literal(embedding)

        cursor.setinputsizes(None, None, oracledb.DB_TYPE_CLOB)

        cursor.execute("""
            INSERT INTO vector_docs (id, content, embedding)
            VALUES (:1, :2, VECTOR(:3))
        """, (10000 + i, text, vector_str))

        if i % BATCH_COMMIT == 0:
            conn.commit()
            print(f"✅ Inserted {i}")

    conn.commit()
    print("✅ Bulk insert complete")


def run_search(cursor, query_text, approx=False):

    query_embedding = generate_embedding(query_text)
    vector_str = to_vector_literal(query_embedding)

    mode = "APPROX" if approx else "EXACT"

    sql = f"""
        SELECT id,
            content,
            VECTOR_DISTANCE(embedding, VECTOR(:1), COSINE) AS distance
        FROM vector_docs
        ORDER BY distance
        FETCH APPROX FIRST 5 ROWS ONLY;
    """

    start = time.time()

    cursor.setinputsizes(oracledb.DB_TYPE_CLOB)
    cursor.execute(sql, [vector_str])
    rows = cursor.fetchall()

    end = time.time()

    print(f"\n🔎 {mode} SEARCH TIME: {end - start:.4f} sec")

    for r in rows:
        print(r)


def main():
    conn = get_connection()
    cursor = conn.cursor()

    print("✅ Connected")

    # bulk_insert(cursor, conn)

    query = "invoice not approved"

    run_search(cursor, query, approx=False)
    run_search(cursor, query, approx=True)

    cursor.close()
    conn.close()

    print("\n🏁 Test complete")


if __name__ == "__main__":
    main()
