#!/usr/bin/env python3
"""
Script para executar migrações do banco de dados
================================================

Execute antes do deploy ou após configurar o banco PostgreSQL.

Uso:
    python run_migrations.py                 # Executar migrações pendentes
    python run_migrations.py --status        # Ver status das migrações
    python run_migrations.py --rollback      # Reverter última migração
"""

import sys
import os
from config import Config

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from migrations.migration_manager import MigrationManager


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Gerenciador de Migrações')
    parser.add_argument('--status', action='store_true', help='Mostrar status das migrações')
    parser.add_argument('--rollback', action='store_true', help='Reverter última migração')
    parser.add_argument('--database-url', help='URL do banco de dados (opcional, usa DATABASE_URL do env)')
    
    args = parser.parse_args()
    
    # Obter URL do banco
    database_url = args.database_url or Config.DATABASE_URL
    
    if not database_url:
        print("❌ ERRO: DATABASE_URL não configurada")
        print("\nDefina a variável de ambiente DATABASE_URL ou use --database-url")
        sys.exit(1)
    
    print(f"\n🔗 Conectando ao banco: {database_url[:30]}...")
    
    # Criar gerenciador
    manager = MigrationManager(database_url)
    
    # Executar comando
    if args.status:
        manager.migration_status()
    elif args.rollback:
        success = manager.rollback_last_migration()
        sys.exit(0 if success else 1)
    else:
        result = manager.run_pending_migrations()
        sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
