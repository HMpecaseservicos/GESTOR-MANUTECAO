#!/usr/bin/env python3
"""
Script para resetar o banco de dados no Fly (remover schema_migrations)
========================================================================

USE COM CUIDADO - Remove todas as migrações registradas para permitir re-execução.
"""

import os
import sys
import psycopg2

def reset_migrations():
    """Remove a tabela schema_migrations para permitir re-execução das migrações"""
    
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ ERRO: DATABASE_URL não está configurada")
        sys.exit(1)
    
    # Corrigir URL se necessário
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    print(f"\n🔗 Conectando ao banco...")
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Listar tabelas existentes
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📋 Tabelas existentes: {tables}")
        
        if not tables:
            print("\n✅ Banco vazio - pronto para migrações")
            return
        
        # Perguntar confirmação
        print("\n⚠️  ATENÇÃO: Este script vai DROPAR todas as tabelas!")
        confirm = input("Digite 'SIM' para continuar: ")
        
        if confirm != 'SIM':
            print("❌ Operação cancelada")
            sys.exit(0)
        
        # Dropar todas as tabelas
        print("\n🗑️  Removendo tabelas...")
        for table in reversed(tables):  # Ordem reversa para respeitar FKs
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                print(f"   ✓ {table}")
            except Exception as e:
                print(f"   ✗ {table}: {e}")
        
        # Dropar funções
        cursor.execute("""
            SELECT proname FROM pg_proc 
            WHERE pronamespace = 'public'::regnamespace
        """)
        
        conn.commit()
        print("\n✅ Banco resetado com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    reset_migrations()
