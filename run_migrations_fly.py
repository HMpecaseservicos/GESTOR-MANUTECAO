#!/usr/bin/env python3
"""
Script simplificado para executar migrações no Fly.io
Não depende de dotenv (usa variáveis de ambiente diretas)
"""

import os
import sys

# Adicionar diretório de migrações ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'migrations'))

from migration_manager import MigrationManager

def main():
    """Executa migrações pendentes"""
    
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL não configurada!")
        return 1
    
    print(f"🔗 Conectando ao banco: PostgreSQL")
    print(f"📂 Diretório de migrações: {os.path.join(os.path.dirname(__file__), 'migrations')}")
    print("")
    
    try:
        # Inicializar gerenciador de migrações
        manager = MigrationManager(
            database_url=DATABASE_URL,
            migrations_dir=os.path.join(os.path.dirname(__file__), 'migrations')
        )
        
        # Executar migrações pendentes
        success = manager.run_pending_migrations()
        
        if success:
            print("\n✅ Todas as migrações foram executadas com sucesso!")
            return 0
        else:
            print("\n❌ Algumas migrações falharam!")
            return 1
            
    except Exception as e:
        print(f"\n❌ Erro ao executar migrações: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
