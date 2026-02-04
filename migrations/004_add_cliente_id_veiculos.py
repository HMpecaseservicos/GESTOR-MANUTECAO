"""
Migração 004: Adicionar cliente_id em veiculos
===============================================

OBJETIVO: Permitir que veículos pertençam a clientes (modo SERVICO)

MUDANÇAS:
- Adiciona coluna cliente_id NULLABLE na tabela veiculos
- Adiciona FK para clientes
- Regras: FROTA → cliente_id NULL, SERVICO → cliente_id obrigatório
- Índice para performance

REVERSÍVEL: Sim (DROP COLUMN no PostgreSQL)
SEGURO PARA PRODUÇÃO: Sim (coluna nullable, não quebra sistema existente)
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Adiciona cliente_id na tabela veiculos"""
    
    name = "Adicionar cliente_id em veiculos"
    
    def up(self):
        """Aplicar migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.is_postgres:
                # PostgreSQL
                print("   📝 Adicionando coluna cliente_id em veiculos...")
                
                # Verificar se coluna já existe
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='veiculos' AND column_name='cliente_id'
                """)
                
                if not cursor.fetchone():
                    # Adicionar coluna
                    cursor.execute("""
                        ALTER TABLE veiculos 
                        ADD COLUMN cliente_id BIGINT
                    """)
                    
                    # Adicionar FK (com ON DELETE CASCADE para limpar automaticamente)
                    cursor.execute("""
                        ALTER TABLE veiculos
                        ADD CONSTRAINT fk_veiculos_cliente 
                        FOREIGN KEY (cliente_id) 
                        REFERENCES clientes(id) 
                        ON DELETE CASCADE
                    """)
                    
                    # Criar índice
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_veiculos_cliente_id 
                        ON veiculos(cliente_id) WHERE cliente_id IS NOT NULL
                    """)
                    
                    # Índice composto para empresas modo SERVICO
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_veiculos_empresa_cliente 
                        ON veiculos(empresa_id, cliente_id)
                    """)
                    
                    print("   ✅ Coluna cliente_id adicionada com sucesso")
                else:
                    print("   ℹ️  Coluna cliente_id já existe")
            
            else:
                # SQLite
                print("   📝 Adicionando coluna cliente_id em veiculos (SQLite)...")
                
                # Verificar se coluna já existe
                cursor.execute("PRAGMA table_info(veiculos)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'cliente_id' not in columns:
                    # Adicionar coluna
                    cursor.execute("""
                        ALTER TABLE veiculos 
                        ADD COLUMN cliente_id INTEGER
                        REFERENCES clientes(id) ON DELETE CASCADE
                    """)
                    
                    # Criar índices
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_veiculos_cliente_id 
                        ON veiculos(cliente_id)
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_veiculos_empresa_cliente 
                        ON veiculos(empresa_id, cliente_id)
                    """)
                    
                    print("   ✅ Coluna cliente_id adicionada com sucesso")
                else:
                    print("   ℹ️  Coluna cliente_id já existe")
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao aplicar migração 004: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def down(self):
        """Reverter migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.is_postgres:
                print("   📝 Removendo coluna cliente_id de veiculos...")
                
                # Remover índices
                cursor.execute("DROP INDEX IF EXISTS idx_veiculos_cliente_id")
                cursor.execute("DROP INDEX IF EXISTS idx_veiculos_empresa_cliente")
                
                # Remover FK
                cursor.execute("""
                    ALTER TABLE veiculos 
                    DROP CONSTRAINT IF EXISTS fk_veiculos_cliente
                """)
                
                # Remover coluna
                cursor.execute("ALTER TABLE veiculos DROP COLUMN IF EXISTS cliente_id")
                
                print("   ✅ Coluna cliente_id removida")
            
            else:
                # SQLite não suporta DROP COLUMN facilmente
                print("   ⚠️  SQLite: não é possível remover coluna facilmente")
                print("   ℹ️  Mantenha a coluna ou recrie a tabela manualmente")
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao reverter migração 004: {e}")
        finally:
            cursor.close()
            conn.close()
