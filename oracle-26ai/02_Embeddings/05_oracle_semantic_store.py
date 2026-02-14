import oracledb
from google import genai
import json

# =============================
# CONFIG
# =============================

DB_CONFIG = {
    "user": "ea_app",
    "password": "EaApp123",
    "dsn": "localhost:1521/FREEPDB1"
}

VECTOR_DIM = 3072
client = genai.Client()


# =============================
# VECTOR GENERATION
# =============================

def generate_vector(text: str):
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )
    return result.embeddings[0].values


def to_clob_vector(vec):
    return "[" + ", ".join(map(str, vec)) + "]"


# =============================
# SERVICE
# =============================

class OracleSemanticStoreService:

    def __init__(self):
        self.conn = oracledb.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor()

    def _table(self, store):
        return f"SS_{store.upper()}"

    # -------------------------
    # STORE LIFECYCLE
    # -------------------------

    def create_semantic_store(self, store):
        # table = self._table(store)
        table = self._table(store)

        self.cursor.execute(f"""
        BEGIN
            EXECUTE IMMEDIATE '
                CREATE TABLE {table} (
                    content_id VARCHAR2(100) PRIMARY KEY,
                    content    CLOB,
                    attributes JSON,
                    vector     VECTOR({VECTOR_DIM}, FLOAT32)
                )';
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE != -955 THEN
                    RAISE;
                END IF;
        END;
        """)

        self.cursor.execute(f"""
        BEGIN
            EXECUTE IMMEDIATE '
                CREATE VECTOR INDEX {table}_VIDX
                ON {table}(vector)
                ORGANIZATION INMEMORY GRAPH
                DISTANCE COSINE';
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE != -955 THEN
                    RAISE;
                END IF;
        END;
        """)

        self.conn.commit()

        print(f"✅ Store ready: {store}")

    def drop_semantic_store(self, store):
        table = self._table(store)
        self.cursor.execute(f"DROP TABLE {table} PURGE")
        self.conn.commit()

    def list_semantic_stores(self):
        self.cursor.execute("""
        SELECT table_name
        FROM user_tables
        WHERE table_name LIKE 'SS_%'
        """)
        print(self.cursor.fetchall())

    # -------------------------
    # CONTENT OPERATIONS
    # -------------------------

    import json
    import oracledb

    def merge_content(self, store, content_id, content, attributes):

        # Resolve physical table name
        table = self._table(store)

        # Generate embedding vector
        vector = to_clob_vector(generate_vector(content))

        # Convert Python dict -> JSON string
        attributes_json = json.dumps(attributes)

        sql = f"""
        MERGE INTO {table} t
        USING (SELECT :id AS content_id FROM dual) s
        ON (t.content_id = s.content_id)

        WHEN MATCHED THEN
            UPDATE SET
                content    = :content,
                attributes = :attr,
                vector     = VECTOR(:vec)

        WHEN NOT MATCHED THEN
            INSERT (content_id, content, attributes, vector)
            VALUES (:id, :content, :attr, VECTOR(:vec))
        """

        # Tell driver the large bind is a CLOB
        self.cursor.setinputsizes(vec=oracledb.DB_TYPE_CLOB)

        # Execute MERGE
        self.cursor.execute(sql, {
            "id": content_id,
            "content": content,
            "attr": attributes_json,
            "vec": vector
        })

        self.conn.commit()

        print(f"✅ Content merged → {content_id}")

    def fetch_content_by_id(self, store, content_id):

        table = self._table(store)

        self.cursor.execute(f"""
        SELECT content_id, content, attributes
        FROM {table}
        WHERE content_id = :1
        """, [content_id])

        print(self.cursor.fetchall())

    def remove_content(self, store, content_id):

        table = self._table(store)

        self.cursor.execute(f"""
        DELETE FROM {table}
        WHERE content_id = :1
        """, [content_id])

        self.conn.commit()

    def get_store_stats(self, store):

        table = self._table(store)

        self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
        print("Content count:", self.cursor.fetchone()[0])

    # -------------------------
    # RETRIEVAL
    # -------------------------

    def semantic_search(self, store, query_text, top_k=3):

        table = self._table(store)

        vector = to_clob_vector(generate_vector(query_text))

        sql = f"""
        SELECT content_id,
            content,
            VECTOR_DISTANCE(vector, VECTOR(:vec), COSINE) AS distance
        FROM {table}
        ORDER BY distance
        FETCH APPROX FIRST :top_k ROWS ONLY
        """

        self.cursor.setinputsizes(vec=oracledb.DB_TYPE_CLOB)

        self.cursor.execute(sql, {
            "vec": vector,
            "top_k": top_k
        })

        rows = self.cursor.fetchall()

        print("\n🔎 Semantic Search Results")
        print("------------------------------------------------------------")
        print(f"{'Rank':<5} {'ID':<10} {'Distance':<12} {'Similarity %':<15} Content")
        print("------------------------------------------------------------")

        for rank, row in enumerate(rows, start=1):

            content_id = row[0]

            # Read CLOB
            content_text = row[1].read()

            distance = row[2]
            similarity = 1 - distance

            print(f"{rank:<5} {content_id:<10} {distance:<12.4f} {similarity:<15.2%} {content_text}")

        print()

    def semantic_search_with_attribute_filter(self, store, query_text, attr_key, attr_value):

        table = self._table(store)
        vector = to_clob_vector(generate_vector(query_text))

        self.cursor.setinputsizes(oracledb.DB_TYPE_CLOB)

        self.cursor.execute(f"""
        SELECT content_id, content
        FROM {table}
        WHERE JSON_VALUE(attributes, '$.{attr_key}') = :2
        ORDER BY VECTOR_DISTANCE(vector, VECTOR(:1), COSINE)
        FETCH APPROX FIRST 3 ROWS ONLY
        """, [vector, attr_value])

        for row in self.cursor:
            print(row)

svc = OracleSemanticStoreService()

svc.create_semantic_store("programming_knowledge")

svc.merge_content(
    "programming_knowledge",
    "1",
    "Python is a programming language",
    {"type": "language"}
)

svc.semantic_search(
    "programming_knowledge",
    "scripting language"
)

svc.get_store_stats("programming_knowledge")
svc.list_semantic_stores()
