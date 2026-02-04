"""
Script de inicialização para produção (Fly.io)
===============================================

Este script:
1. Executa as migrações do banco de dados
2. Inicializa o sistema se necessário
3. Inicia a aplicação

Usado automaticamente pelo Fly.io no deploy.
"""

import os
import sys
from config import Config
from migrations.migration_manager import MigrationManager


def init_production():
    """Inicializar sistema em produção"""
    print("\n" + "="*70)
    print("🚀 INICIALIZANDO SISTEMA EM PRODUÇÃO")
    print("="*70 + "\n")
    
    # Verificar DATABASE_URL
    if not Config.DATABASE_URL or Config.DATABASE_URL.startswith('sqlite'):
        print("❌ ERRO: DATABASE_URL não está configurada para PostgreSQL")
        print("   Configure a variável de ambiente DATABASE_URL no Fly.io")
        sys.exit(1)
    
    print(f"✅ DATABASE_URL configurada")
    print(f"   Tipo: {'PostgreSQL' if Config.IS_POSTGRES else 'SQLite'}\n")
    
    # Executar migrações
    try:
        manager = MigrationManager(Config.DATABASE_URL)
        result = manager.run_pending_migrations()
        
        if not result['success']:
            print("\n❌ ERRO: Falha ao executar migrações")
            sys.exit(1)
        
        print("\n✅ Sistema inicializado com sucesso!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERRO na inicialização: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    init_production()
