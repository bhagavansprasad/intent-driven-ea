import oracledb

conn = oracledb.connect(
    user="ea_app",
    password="EaApp123",
    dsn="localhost:1521/FREEPDB1"
)

cursor = conn.cursor()

cursor.execute("select 'connected' from dual")
print(cursor.fetchone())
