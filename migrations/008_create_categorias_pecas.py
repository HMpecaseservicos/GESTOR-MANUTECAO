"""
Migração 008: Criar tabela de categorias de peças
- Categorias personalizáveis por empresa
- Adiciona campo categoria_id na tabela pecas
"""

def upgrade(cursor, is_postgres=True):
    """Aplica a migração"""
    
    if is_postgres:
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
        
        # Adicionar coluna categoria_id na tabela pecas (se não existir)
        cursor.execute('''
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'pecas' AND column_name = 'categoria_id'
                ) THEN 
                    ALTER TABLE pecas ADD COLUMN categoria_id INTEGER REFERENCES categorias_pecas(id);
                END IF;
            END $$;
        ''')
        
        # Criar índices
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_categorias_pecas_empresa 
            ON categorias_pecas(empresa_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_pecas_categoria 
            ON pecas(categoria_id)
        ''')
        
    else:
        # SQLite
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categorias_pecas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                nome VARCHAR(100) NOT NULL,
                descricao TEXT,
                cor VARCHAR(20) DEFAULT '#6c757d',
                icone VARCHAR(50) DEFAULT 'fas fa-tag',
                ativo BOOLEAN DEFAULT 1,
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
    
    print("✅ Migração 008: Tabela categorias_pecas criada com sucesso!")


def downgrade(cursor, is_postgres=True):
    """Reverte a migração"""
    
    if is_postgres:
        cursor.execute('ALTER TABLE pecas DROP COLUMN IF EXISTS categoria_id')
        cursor.execute('DROP TABLE IF EXISTS categorias_pecas')
    else:
        # SQLite não suporta DROP COLUMN facilmente
        cursor.execute('DROP TABLE IF EXISTS categorias_pecas')
    
    print("⬇️ Migração 008 revertida")
