"""
Gerenciador de Migrações para PostgreSQL
=========================================

Sistema de versionamento de banco de dados para preparação do modelo híbrido.
Suporta PostgreSQL e SQLite (dev local).
"""

import os
import importlib
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict


class MigrationManager:
    """Gerenciador de migrações do banco de dados"""
    
    def __init__(self, database_url: str):
        """
        Inicializa o gerenciador de migrações
        
        Args:
            database_url: URL de conexão do banco (PostgreSQL ou SQLite)
        """
        self.database_url = database_url
        self.is_postgres = database_url.startswith('postgresql://') or database_url.startswith('postgres://')
        self.migrations_dir = os.path.dirname(__file__)
        
    def get_connection(self):
        """Obtém conexão com o banco de dados"""
        if self.is_postgres:
            return psycopg2.connect(self.database_url)
        else:
            # SQLite para desenvolvimento local
            db_path = self.database_url.replace('sqlite:///', '')
            return sqlite3.connect(db_path)
    
    def ensure_migrations_table(self):
        """Garante que a tabela de controle de migrações existe"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.is_postgres:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(500) NOT NULL,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INTEGER,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INTEGER,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT
                )
            """)
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def get_applied_migrations(self) -> List[str]:
        """Retorna lista de migrações já aplicadas"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT version FROM schema_migrations WHERE success = TRUE ORDER BY version"
                if self.is_postgres else
                "SELECT version FROM schema_migrations WHERE success = 1 ORDER BY version"
            )
            
            if self.is_postgres:
                migrations = [row[0] for row in cursor.fetchall()]
            else:
                migrations = [row[0] for row in cursor.fetchall()]
            
            return migrations
        except Exception:
            return []
        finally:
            cursor.close()
            conn.close()
    
    def get_pending_migrations(self) -> List[tuple]:
        """Retorna lista de migrações pendentes"""
        applied = set(self.get_applied_migrations())
        all_migrations = []
        
        # Listar todos os arquivos de migração
        for filename in sorted(os.listdir(self.migrations_dir)):
            if filename.endswith('.py') and filename[0].isdigit():
                version = filename.replace('.py', '')
                if version not in applied:
                    all_migrations.append((version, filename))
        
        return all_migrations
    
    def run_migration(self, version: str, filename: str) -> bool:
        """
        Executa uma migração específica
        
        Args:
            version: Versão da migração (ex: '001_add_tipo_operacao_empresas')
            filename: Nome do arquivo (ex: '001_add_tipo_operacao_empresas.py')
        
        Returns:
            True se sucesso, False caso contrário
        """
        print(f"\n🔄 Executando migração: {version}")
        
        start_time = datetime.now()
        
        try:
            # Importar módulo da migração
            module_name = f"migrations.{filename.replace('.py', '')}"
            migration_module = importlib.import_module(module_name)
            
            # Obter classe de migração
            migration_class = getattr(migration_module, 'Migration')
            migration = migration_class(self.database_url, self.is_postgres)
            
            # Executar migração
            migration.up()
            
            # Registrar sucesso
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            self._record_migration(version, migration.name, execution_time, True, None)
            
            print(f"✅ Migração {version} aplicada com sucesso ({execution_time}ms)")
            return True
            
        except Exception as e:
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            error_msg = str(e)
            self._record_migration(version, version, execution_time, False, error_msg)
            
            print(f"❌ Erro ao aplicar migração {version}: {error_msg}")
            return False
    
    def _record_migration(self, version: str, name: str, execution_time: int, 
                         success: bool, error_message: Optional[str]):
        """Registra execução da migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.is_postgres:
            cursor.execute("""
                INSERT INTO schema_migrations 
                (version, name, execution_time_ms, success, error_message)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (version) DO UPDATE SET
                    applied_at = CURRENT_TIMESTAMP,
                    execution_time_ms = EXCLUDED.execution_time_ms,
                    success = EXCLUDED.success,
                    error_message = EXCLUDED.error_message
            """, (version, name, execution_time, success, error_message))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO schema_migrations 
                (version, name, execution_time_ms, success, error_message)
                VALUES (?, ?, ?, ?, ?)
            """, (version, name, execution_time, 1 if success else 0, error_message))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def run_pending_migrations(self) -> Dict[str, any]:
        """
        Executa todas as migrações pendentes
        
        Returns:
            Dicionário com resultados da execução
        """
        print("\n" + "="*70)
        print("🚀 INICIANDO MIGRAÇÕES DO BANCO DE DADOS")
        print("="*70)
        
        # Garantir tabela de controle
        self.ensure_migrations_table()
        
        # Obter migrações pendentes
        pending = self.get_pending_migrations()
        
        if not pending:
            print("\n✅ Não há migrações pendentes. Banco de dados está atualizado!")
            return {'success': True, 'migrations_run': 0, 'errors': []}
        
        print(f"\n📋 Encontradas {len(pending)} migração(ões) pendente(s)")
        
        # Executar migrações
        results = {'success': True, 'migrations_run': 0, 'errors': []}
        
        for version, filename in pending:
            success = self.run_migration(version, filename)
            
            if success:
                results['migrations_run'] += 1
            else:
                results['success'] = False
                results['errors'].append(version)
                print(f"\n⚠️  Parando execução devido a erro na migração {version}")
                break
        
        print("\n" + "="*70)
        if results['success']:
            print(f"✅ MIGRAÇÕES CONCLUÍDAS COM SUCESSO!")
            print(f"   {results['migrations_run']} migração(ões) aplicada(s)")
        else:
            print(f"❌ ERRO NAS MIGRAÇÕES")
            print(f"   {results['migrations_run']} aplicada(s), {len(results['errors'])} falhou")
        print("="*70 + "\n")
        
        return results
    
    def rollback_last_migration(self) -> bool:
        """Reverte a última migração aplicada"""
        applied = self.get_applied_migrations()
        
        if not applied:
            print("ℹ️  Não há migrações para reverter")
            return True
        
        last_version = applied[-1]
        filename = f"{last_version}.py"
        
        print(f"\n🔄 Revertendo migração: {last_version}")
        
        try:
            # Importar módulo da migração
            module_name = f"migrations.{last_version}"
            migration_module = importlib.import_module(module_name)
            
            # Obter classe de migração
            migration_class = getattr(migration_module, 'Migration')
            migration = migration_class(self.database_url, self.is_postgres)
            
            # Executar rollback
            migration.down()
            
            # Remover registro
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.is_postgres:
                cursor.execute("DELETE FROM schema_migrations WHERE version = %s", (last_version,))
            else:
                cursor.execute("DELETE FROM schema_migrations WHERE version = ?", (last_version,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Migração {last_version} revertida com sucesso")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao reverter migração {last_version}: {e}")
            return False
    
    def migration_status(self):
        """Exibe status das migrações"""
        print("\n" + "="*70)
        print("📊 STATUS DAS MIGRAÇÕES")
        print("="*70 + "\n")
        
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        print(f"✅ Aplicadas: {len(applied)}")
        for version in applied:
            print(f"   - {version}")
        
        if pending:
            print(f"\n⏳ Pendentes: {len(pending)}")
            for version, _ in pending:
                print(f"   - {version}")
        else:
            print(f"\n⏳ Pendentes: 0")
        
        print("\n" + "="*70 + "\n")


class BaseMigration:
    """Classe base para migrações"""
    
    def __init__(self, database_url: str, is_postgres: bool):
        self.database_url = database_url
        self.is_postgres = is_postgres
        self.name = self.__class__.__name__
    
    def get_connection(self):
        """Obtém conexão com o banco"""
        if self.is_postgres:
            return psycopg2.connect(self.database_url)
        else:
            db_path = self.database_url.replace('sqlite:///', '')
            return sqlite3.connect(db_path)
    
    def execute(self, query: str, params: tuple = None):
        """Executa uma query"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
        finally:
            cursor.close()
            conn.close()
    
    def up(self):
        """Aplicar migração - deve ser sobrescrito"""
        raise NotImplementedError("Método up() deve ser implementado")
    
    def down(self):
        """Reverter migração - deve ser sobrescrito"""
        raise NotImplementedError("Método down() deve ser implementado")
