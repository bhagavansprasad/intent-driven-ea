🔹 Option A — AI SQL & Vector deep dive
cosine / dot-product similarity
vector indexes
hybrid SQL + vector queries

🔹 Option B — Agent integration
JDBC / Python connection

embedding ingestion pipeline

intent → SQL → vector flow

##### Running Docker image
```
docker run -d   --name oracle26ai_db_bhagavan   -p 1521:1521   -e ORACLE_PWD=Abcd1234   -e ORACLE_CHARACTERSET=AL32UTF8   -v ~/oracle_oradata:/opt/oracle/oradata   container-registry.oracle.com/database/free:latest

- Start Docker container
docker start oracle26ai_db_bhagavan
```
- Logging to SYSDBA (CDB)
docker exec -it oracle26ai_db_bhagavan sqlplus sys/Abcd1234@FREE as sysdba

- Application access (PDB)
docker exec -it oracle26ai_db_bhagavan sqlplus system/Abcd1234@FREEPDB1

- SQL commands
* Print Version
SELECT banner_full FROM v$version;

- Create User 'ea_app'
CREATE USER ea_app IDENTIFIED BY EaApp123
  DEFAULT TABLESPACE users
  TEMPORARY TABLESPACE temp
  QUOTA UNLIMITED ON users;

- Grant prveliges
GRANT connect, resource TO ea_app;
GRANT create table, create procedure, create view TO ea_app;

- Creating Table 'embeddings_test'
ALTER SESSION SET CONTAINER=FREEPDB1;

CREATE TABLE embeddings_test (
  id NUMBER,
  embedding VECTOR(3, FLOAT32)
);

- Insert Rows
INSERT INTO embeddings_test VALUES (
  1,
  VECTOR('[0.12, 0.98, 0.33]')
);

- Dump rows
SELECT * FROM embeddings_test;

- Login with 'ea_app' user
docker exec -it oracle26ai_db_bhagavan sqlplus ea_app/EaApp123@FREEPDB1

- List tables
SELECT table_name FROM user_tables ORDER BY table_name;
SELECT table_name, column_name, data_type FROM user_tab_columns WHERE data_type = 'VECTOR';

- Vector Index - This enables fast similarity search.
- Without index → brute-force scan, With index → Approximate Nearest Neighbor (ANN)
CREATE VECTOR INDEX emb_idx ON embeddings_test(embedding) ORGANIZATION HNSW;

- Key point
Oracle 26ai = Relational DB (JSON DB, Graph DB, Vector DB, ML Engine).  
All inside ONE database engine

- Vectory DB operations

- Show which db is connected with
SHOW CON_NAME;

- Change db
ALTER SESSION SET CONTAINER = FREEPDB1;

CREATE TABLE vector_docs (
    id        NUMBER PRIMARY KEY,
    content   VARCHAR2(200),
    embedding VECTOR(3, FLOAT32)
);


DESC vector_docs;
INSERT INTO vector_docs VALUES (
  1,
  'Invoice pending approval',
  VECTOR('[0.1, 0.2, 0.3]')
);

INSERT INTO vector_docs VALUES (
  2,
  'Payment processed successfully',
  VECTOR('[0.9, 0.1, 0.4]')
);

INSERT INTO vector_docs VALUES (
  3,
  'Customer dispute raised',
  VECTOR('[0.2, 0.8, 0.5]')
);

COMMIT;
SELECT id, content FROM vector_docs;
SELECT id,
       content,
       VECTOR_DISTANCE(
           embedding,
           VECTOR('[0.1, 0.2, 0.25]'),
           COSINE
       ) AS distance
FROM vector_docs
ORDER BY distance
FETCH FIRST 3 ROWS ONLY;

SET LINESIZE 200
SET PAGESIZE 100
SET LONG 10000
SET LONGCHUNKSIZE 10000
SET TRIMSPOOL ON
SET WRAP OFF

COLUMN id FORMAT 999
COLUMN content FORMAT A40
COLUMN distance FORMAT 0.000000

UPDATE vector_docs
SET embedding = VECTOR('[0.15, 0.25, 0.35]')
WHERE id = 1;

COMMIT;
SELECT id, embedding FROM vector_docs WHERE id = 1;
DELETE FROM vector_docs WHERE id = 3;
COMMIT;
SELECT * FROM vector_docs;

CREATE VECTOR INDEX vector_docs_idx
ON vector_docs (embedding)
ORGANIZATION INMEMORY;

CREATE VECTOR INDEX emb_idx ON vector_docs(embedding) ORGANIZATION HNSW;
