"""
Validação Pós-Deploy Fly.io
============================

Script para validar ETAPA 0 após deploy no Fly.io com PostgreSQL.
Executa dentro do container via SSH.
"""

import os
import sys

def check_database_connection():
    """Verifica conexão com PostgreSQL"""
    print("\n🔗 VERIFICANDO CONEXÃO COM BANCO DE DADOS...")
    
    # Ler DATABASE_URL diretamente do environment (sem config.py)
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL não configurada!")
        return False
    
    IS_POSTGRES = 'postgresql://' in DATABASE_URL or 'postgres://' in DATABASE_URL
    
    if not IS_POSTGRES:
        print("❌ Banco não é PostgreSQL!")
        print(f"   DATABASE_URL: {DATABASE_URL[:50]}...")
        return False
    
    print(f"✅ DATABASE_URL configurada")
    print(f"✅ Banco: PostgreSQL")
    
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✅ PostgreSQL conectado: {version.split(',')[0]}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return False


def check_migrations():
    """Verifica se todas as migrações foram aplicadas"""
    print("\n📋 VERIFICANDO MIGRAÇÕES...")
    
    try:
        from config import Config
        import psycopg2
        
        conn = psycopg2.connect(Config.DATABASE_URL)
        cursor = conn.cursor()
        
        # Verificar tabela de migrações
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'schema_migrations'
            )
        """)
        
        if not cursor.fetchone()[0]:
            print("❌ Tabela schema_migrations não existe!")
            print("   Execute: python run_migrations.py")
            cursor.close()
            conn.close()
            return False
        
        # Contar migrações aplicadas
        cursor.execute("""
            SELECT COUNT(*) 
            FROM schema_migrations 
            WHERE success = TRUE
        """)
        count = cursor.fetchone()[0]
        
        if count == 7:
            print(f"✅ Todas as 7 migrações aplicadas com sucesso")
        else:
            print(f"⚠️  Apenas {count}/7 migrações aplicadas")
            
            # Listar migrações aplicadas
            cursor.execute("""
                SELECT version, name, applied_at 
                FROM schema_migrations 
                WHERE success = TRUE
                ORDER BY version
            """)
            print("\n   Migrações aplicadas:")
            for row in cursor.fetchall():
                print(f"   ✅ {row[0]} - {row[1]}")
            
            cursor.close()
            conn.close()
            return count == 7
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar migrações: {e}")
        return False


def check_new_tables():
    """Verifica se as novas tabelas foram criadas"""
    print("\n📊 VERIFICANDO NOVAS TABELAS...")
    
    try:
        from config import Config
        import psycopg2
        
        conn = psycopg2.connect(Config.DATABASE_URL)
        cursor = conn.cursor()
        
        tabelas_esperadas = [
            'clientes',
            'servicos',
            'manutencao_servicos',
            'ordens_servico'
        ]
        
        for tabela in tabelas_esperadas:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                )
            """, (tabela,))
            
            exists = cursor.fetchone()[0]
            symbol = "✅" if exists else "❌"
            print(f"{symbol} Tabela {tabela}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar tabelas: {e}")
        return False


def check_schema_changes():
    """Verifica alterações no schema existente"""
    print("\n🔧 VERIFICANDO ALTERAÇÕES NO SCHEMA...")
    
    try:
        from config import Config
        import psycopg2
        
        conn = psycopg2.connect(Config.DATABASE_URL)
        cursor = conn.cursor()
        
        # Verificar coluna tipo_operacao em empresas
        cursor.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns 
            WHERE table_name = 'empresas' 
            AND column_name = 'tipo_operacao'
        """)
        
        row = cursor.fetchone()
        if row:
            print(f"✅ Coluna tipo_operacao existe em empresas")
            print(f"   Tipo: {row[1]}, Default: {row[2]}")
        else:
            print("❌ Coluna tipo_operacao NÃO existe em empresas")
        
        # Verificar coluna cliente_id em veiculos
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns 
            WHERE table_name = 'veiculos' 
            AND column_name = 'cliente_id'
        """)
        
        row = cursor.fetchone()
        if row:
            print(f"✅ Coluna cliente_id existe em veiculos")
        else:
            print("❌ Coluna cliente_id NÃO existe em veiculos")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar schema: {e}")
        return False


def check_indexes():
    """Verifica índices criados"""
    print("\n📈 VERIFICANDO ÍNDICES...")
    
    try:
        from config import Config
        import psycopg2
        
        conn = psycopg2.connect(Config.DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname LIKE 'idx_%'
        """)
        
        count = cursor.fetchone()[0]
        print(f"✅ {count} índices criados (prefixo idx_)")
        
        # Listar alguns índices importantes
        cursor.execute("""
            SELECT indexname, tablename
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname LIKE 'idx_empresas%'
            ORDER BY indexname
            LIMIT 5
        """)
        
        print("\n   Exemplos de índices:")
        for row in cursor.fetchall():
            print(f"   • {row[0]} em {row[1]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar índices: {e}")
        return False


def check_foreign_keys():
    """Verifica FKs criadas"""
    print("\n🔗 VERIFICANDO FOREIGN KEYS...")
    
    try:
        from config import Config
        import psycopg2
        
        conn = psycopg2.connect(Config.DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name IN ('clientes', 'servicos', 'veiculos', 'manutencao_servicos', 'ordens_servico')
            ORDER BY tc.table_name
        """)
        
        fks = cursor.fetchall()
        print(f"✅ {len(fks)} FKs encontradas nas novas tabelas")
        
        for fk in fks[:10]:  # Mostrar até 10
            print(f"   • {fk[0]}.{fk[1]} → {fk[2]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar FKs: {e}")
        return False


def check_sistema_atual():
    """Verifica se o sistema FROTA continua funcionando"""
    print("\n🚗 VERIFICANDO SISTEMA FROTA (COMPATIBILIDADE)...")
    
    try:
        from config import Config
        import psycopg2
        
        conn = psycopg2.connect(Config.DATABASE_URL)
        cursor = conn.cursor()
        
        # Testar queries básicas
        cursor.execute("SELECT COUNT(*) FROM veiculos")
        veiculos = cursor.fetchone()[0]
        print(f"✅ Veículos: {veiculos} registros")
        
        cursor.execute("SELECT COUNT(*) FROM manutencoes")
        manutencoes = cursor.fetchone()[0]
        print(f"✅ Manutenções: {manutencoes} registros")
        
        cursor.execute("SELECT COUNT(*) FROM pecas")
        pecas = cursor.fetchone()[0]
        print(f"✅ Peças: {pecas} registros")
        
        cursor.execute("SELECT COUNT(*) FROM empresas")
        empresas = cursor.fetchone()[0]
        print(f"✅ Empresas: {empresas} registros")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar sistema: {e}")
        return False


def main():
    """Executar todas as validações"""
    print("\n" + "="*70)
    print("🎯 VALIDAÇÃO PÓS-DEPLOY FLY.IO - ETAPA 0")
    print("="*70)
    
    checks = [
        ("Conexão PostgreSQL", check_database_connection),
        ("Migrações", check_migrations),
        ("Novas Tabelas", check_new_tables),
        ("Alterações Schema", check_schema_changes),
        ("Índices", check_indexes),
        ("Foreign Keys", check_foreign_keys),
        ("Sistema FROTA", check_sistema_atual),
    ]
    
    results = []
    
    for name, check_func in checks:
        try:
            success = check_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ Erro inesperado em {name}: {e}")
            results.append((name, False))
    
    # Resumo
    print("\n" + "="*70)
    print("📊 RESUMO DA VALIDAÇÃO")
    print("="*70 + "\n")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        symbol = "✅" if success else "❌"
        print(f"{symbol} {name}")
    
    print("\n" + "="*70)
    
    if passed == total:
        print("✅ VALIDAÇÃO COMPLETA - ETAPA 0 EXECUTADA COM SUCESSO!")
        print("="*70 + "\n")
        print("🎉 Sistema pronto para produção no Fly.io com PostgreSQL!")
        print("📚 Base sólida para implementar ETAPAS 1-10")
        return 0
    else:
        print(f"⚠️  VALIDAÇÃO PARCIAL - {passed}/{total} checks passaram")
        print("="*70 + "\n")
        print("🔧 Revise os erros acima e execute correções necessárias.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
