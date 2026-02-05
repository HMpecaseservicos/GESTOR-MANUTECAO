"""
Migração 008: Criar tabela de categorias de peças
=================================================

OBJETIVO: Permitir categorização de peças (Peças Hidráulicas, Pneus, Filtros, etc.)

MUDANÇAS:
- Cria tabela categorias_pecas com empresa_id para multi-tenant
- Adiciona coluna categoria_id na tabela pecas
- Cria índices para performance

REVERSÍVEL: Sim
SEGURO PARA PRODUÇÃO: Sim
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Cria sistema de categorias para peças"""
    
    name = "Criar categorias de peças"
    
    def up(self):
        """Aplicar migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.is_postgres:
                print("   📝 Criando tabela categorias_pecas...")
                
                # Criar tabela de categorias
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS categorias_pecas (
                        id SERIAL PRIMARY KEY,
                        empresa_id INTEGER NOT NULL,
                        nome VARCHAR(100) NOT NULL,
                        descricao TEXT,
                        cor VARCHAR(20) DEFAULT '#6c757d',
                        icone VARCHAR(50) DEFAULT 'fas fa-tag',
                        ativo BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(empresa_id, nome)
                    )
                ''')
                
                print("   📝 Adicionando coluna categoria_id em pecas...")
                
                # Verificar se coluna já existe
                cursor.execute('''
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'pecas' AND column_name = 'categoria_id'
                ''')
                
                if not cursor.fetchone():
                    cursor.execute('ALTER TABLE pecas ADD COLUMN categoria_id INTEGER REFERENCES categorias_pecas(id)')
                
                print("   📝 Criando índices...")
                
                # Criar índices
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_categorias_pecas_empresa ON categorias_pecas(empresa_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_pecas_categoria ON pecas(categoria_id)')
                
            else:
                # SQLite
                print("   📝 Criando tabela categorias_pecas...")
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS categorias_pecas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        empresa_id INTEGER NOT NULL,
                        nome VARCHAR(100) NOT NULL,
                        descricao TEXT,
                        cor VARCHAR(20) DEFAULT '#6c757d',
                        icone VARCHAR(50) DEFAULT 'fas fa-tag',
                        ativo INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(empresa_id, nome)
                    )
                ''')
                
                # Verificar se coluna existe
                cursor.execute("PRAGMA table_info(pecas)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'categoria_id' not in columns:
                    cursor.execute('ALTER TABLE pecas ADD COLUMN categoria_id INTEGER')
            
            conn.commit()
            print("   ✅ Tabela categorias_pecas criada com sucesso!")
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def down(self):
        """Reverter migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.is_postgres:
                cursor.execute('ALTER TABLE pecas DROP COLUMN IF EXISTS categoria_id')
                cursor.execute('DROP TABLE IF EXISTS categorias_pecas')
            else:
                cursor.execute('DROP TABLE IF EXISTS categorias_pecas')
            
            conn.commit()
            print("   ⬇️ Migração 008 revertida")
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
