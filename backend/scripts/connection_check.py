import psycopg2
from decouple import config

try:
    database_url = config('DATABASE_URL')
    print(f"🔌 Conectando a Supabase...")
    
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"✅ Conexión exitosa!")
    print(f"📊 PostgreSQL: {version[0][:80]}...")
    
    cursor.execute("""
        SELECT tablename 
        FROM pg_catalog.pg_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename;
    """)
    tables = cursor.fetchall()
    print(f"\n📋 Tablas encontradas: {len(tables)}")
    for table in tables:
        print(f"  ✅ {table[0]}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error de conexión: {e}")
