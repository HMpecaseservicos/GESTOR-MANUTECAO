"""
Validação Pós-Deploy Fly.io - ETAPA 0
Versão simplificada sem dependências de config.py
"""

import os
import sys

DATABASE_URL = os.environ.get('DATABASE_URL', '')

def get_connection():
    """Retorna conexão PostgreSQL"""
    import psycopg2
    return psycopg2.connect(DATABASE_URL)

def check_database():
    """Verifica conexão PostgreSQL"""
    print("\n🔗 VERIFICANDO CONEXÃO PostgreSQL...")
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL não configurada!")
        return False
    
    try:
        import psycopg2
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✅ PostgreSQL: {version.split(',')[0]}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def check_migrations():
    """Verifica migrações aplicadas"""
    print("\n📋 VERIFICANDO MIGRAÇÕES...")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT version, name, success, applied_at 
            FROM schema_migrations 
            ORDER BY version
        """)
        
        migrations = cursor.fetchall()
        
        if not migrations:
            print("❌ Nenhuma migração aplicada!")
            return False
        
        print(f"✅ {len(migrations)} migrações aplicadas:")
        for version, name, success, applied_at in migrations:
            status = "✅" if success else "❌"
            print(f"   {status} {version} - {name}")
        
        # Verificar se todas tiveram sucesso
        failed = [m for m in migrations if not m[2]]
        if failed:
            print(f"❌ {len(failed)} migrações falharam!")
            return False
        
        # Esperamos 7 migrações
        if len(migrations) < 7:
            print(f"⚠️  Esperado: 7 migrações, Encontrado: {len(migrations)}")
            return False
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def check_tables():
    """Verifica novas tabelas"""
    print("\n📊 VERIFICANDO NOVAS TABELAS...")
    
    expected_tables = ['clientes', 'servicos', 'manutencao_servicos', 'ordens_servico']
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = ANY(%s)
            ORDER BY table_name
        """, (expected_tables,))
        
        found = [row[0] for row in cursor.fetchall()]
        
        for table in expected_tables:
            if table in found:
                print(f"✅ Tabela: {table}")
            else:
                print(f"❌ Falta: {table}")
        
        cursor.close()
        conn.close()
        
        return len(found) == len(expected_tables)
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def check_schema_changes():
    """Verifica alterações no schema"""
    print("\n🔧 VERIFICANDO ALTERAÇÕES NO SCHEMA...")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Verificar tipo_operacao em empresas
        cursor.execute("""
            SELECT column_name, data_type, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'empresas' 
            AND column_name = 'tipo_operacao'
        """)
        
        col = cursor.fetchone()
        if col:
            print(f"✅ empresas.tipo_operacao: {col[1]} (default: {col[2]})")
        else:
            print("❌ empresas.tipo_operacao não existe!")
            cursor.close()
            conn.close()
            return False
        
        # 2. Verificar cliente_id em veiculos
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'veiculos' 
            AND column_name = 'cliente_id'
        """)
        
        col = cursor.fetchone()
        if col:
            print(f"✅ veiculos.cliente_id: {col[1]} (nullable: {col[2]})")
        else:
            print("❌ veiculos.cliente_id não existe!")
            cursor.close()
            conn.close()
            return False
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def check_indexes():
    """Verifica índices criados"""
    print("\n📈 VERIFICANDO ÍNDICES...")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname LIKE 'idx_%'
            ORDER BY tablename, indexname
        """)
        
        indexes = cursor.fetchall()
        
        print(f"✅ {len(indexes)} índices encontrados")
        
        # Agrupar por tabela
        tables = {}
        for idx, table in indexes:
            if table not in tables:
                tables[table] = []
            tables[table].append(idx)
        
        for table, idxs in sorted(tables.items()):
            print(f"   {table}: {len(idxs)} índices")
        
        cursor.close()
        conn.close()
        
        return len(indexes) > 0
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def check_foreign_keys():
    """Verifica foreign keys"""
    print("\n🔗 VERIFICANDO FOREIGN KEYS...")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name IN ('clientes', 'servicos', 'manutencao_servicos', 'ordens_servico', 'veiculos')
            ORDER BY tc.table_name
        """)
        
        fks = cursor.fetchall()
        
        print(f"✅ {len(fks)} foreign keys encontradas:")
        for table, column, ref_table in fks:
            if table in ['clientes', 'servicos', 'manutencao_servicos', 'ordens_servico'] or column == 'cliente_id':
                print(f"   {table}.{column} -> {ref_table}")
        
        cursor.close()
        conn.close()
        
        return len(fks) > 0
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def check_system_compatibility():
    """Verifica compatibilidade do sistema FROTA"""
    print("\n🚗 VERIFICANDO SISTEMA FROTA...")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar se todas empresas têm tipo_operacao
        cursor.execute("SELECT COUNT(*) FROM empresas WHERE tipo_operacao IS NULL")
        null_count = cursor.fetchone()[0]
        
        if null_count > 0:
            print(f"❌ {null_count} empresas sem tipo_operacao!")
            return False
        
        print("✅ Todas empresas têm tipo_operacao")
        
        # Verificar se empresas existentes são FROTA
        cursor.execute("SELECT COUNT(*) FROM empresas WHERE tipo_operacao = 'FROTA'")
        frota_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM empresas")
        total_count = cursor.fetchone()[0]
        
        print(f"✅ {frota_count}/{total_count} empresas são FROTA")
        
        # Verificar veículos sem cliente_id (FROTA)
        cursor.execute("SELECT COUNT(*) FROM veiculos WHERE cliente_id IS NULL")
        veiculos_frota = cursor.fetchone()[0]
        
        print(f"✅ {veiculos_frota} veículos no modo FROTA (cliente_id NULL)")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    """Executa validação completa"""
    
    print("\n" + "="*70)
    print("🎯 VALIDAÇÃO PÓS-DEPLOY FLY.IO - ETAPA 0")
    print("="*70)
    
    results = {
        'Conexão PostgreSQL': check_database(),
        'Migrações': check_migrations(),
        'Novas Tabelas': check_tables(),
        'Alterações Schema': check_schema_changes(),
        'Índices': check_indexes(),
        'Foreign Keys': check_foreign_keys(),
        'Sistema FROTA': check_system_compatibility()
    }
    
    print("\n" + "="*70)
    print("📊 RESUMO DA VALIDAÇÃO")
    print("="*70)
    
    for check, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    
    print("\n" + "="*70)
    if passed_count == total_count:
        print(f"✅ VALIDAÇÃO COMPLETA - {passed_count}/{total_count} checks passaram")
        print("="*70)
        print("\n🎉 ETAPA 0 CONCLUÍDA COM SUCESSO!")
        print("   Sistema pronto para uso no Fly.io com PostgreSQL")
        return 0
    else:
        print(f"⚠️  VALIDAÇÃO PARCIAL - {passed_count}/{total_count} checks passaram")
        print("="*70)
        print("\n🔧 Revise os erros acima e execute correções necessárias.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
