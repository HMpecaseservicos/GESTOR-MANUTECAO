import psycopg2
import os

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Verificar tabela de migrações
cur.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'schema_migrations'
    )
""")

if cur.fetchone()[0]:
    # Ver migrações aplicadas
    cur.execute("SELECT version, name, success FROM schema_migrations ORDER BY version")
    migrations = cur.fetchall()
    print(f"\n✅ {len(migrations)} migrações aplicadas:")
    for v, n, s in migrations:
        status = "✅" if s else "❌"
        print(f"  {status} {v} - {n}")
    
    # Ver tabelas criadas
    cur.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('clientes', 'servicos', 'manutencao_servicos', 'ordens_servico')
        ORDER BY table_name
    """)
    tables = cur.fetchall()
    print(f"\n✅ {len(tables)} novas tabelas:")
    for t in tables:
        print(f"  - {t[0]}")
    
    # Verificar colunas adicionadas
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'empresas' AND column_name = 'tipo_operacao'
    """)
    if cur.fetchone():
        print("\n✅ Coluna empresas.tipo_operacao adicionada")
    
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'veiculos' AND column_name = 'cliente_id'
    """)
    if cur.fetchone():
        print("✅ Coluna veiculos.cliente_id adicionada")
    
    print("\n🎉 ETAPA 0 CONCLUÍDA COM SUCESSO!")
else:
    print("❌ Tabela schema_migrations não existe - migrações não foram executadas")

conn.close()
