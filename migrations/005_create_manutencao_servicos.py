"""
Migração 005: Criar tabela manutencao_servicos
===============================================

OBJETIVO: Vincular serviços (do catálogo ou avulsos) às manutenções

MUDANÇAS:
- Cria tabela de itens de serviço por manutenção
- Permite vincular ao catálogo (servico_id) ou criar avulso (servico_id NULL)
- Suporta quantidade, valor unitário e subtotal
- FK para manutencoes e servicos (opcional)

REVERSÍVEL: Sim (DROP TABLE)
SEGURO PARA PRODUÇÃO: Sim (tabela nova, não afeta sistema existente)
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Cria tabela manutencao_servicos"""
    
    name = "Criar tabela manutencao_servicos"
    
    def up(self):
        """Aplicar migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.is_postgres:
                # PostgreSQL
                print("   📝 Criando tabela manutencao_servicos...")
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS manutencao_servicos (
                        id BIGSERIAL PRIMARY KEY,
                        manutencao_id BIGINT NOT NULL,
                        servico_id BIGINT,
                        nome_servico VARCHAR(200) NOT NULL,
                        descricao TEXT,
                        quantidade DECIMAL(10,2) DEFAULT 1.00 CHECK(quantidade > 0),
                        valor_unitario DECIMAL(10,2) DEFAULT 0.00 CHECK(valor_unitario >= 0),
                        subtotal DECIMAL(10,2) GENERATED ALWAYS AS (quantidade * valor_unitario) STORED,
                        observacoes TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        
                        CONSTRAINT fk_manutencao_servicos_manutencao 
                            FOREIGN KEY (manutencao_id) 
                            REFERENCES manutencoes(id) 
                            ON DELETE CASCADE,
                        
                        CONSTRAINT fk_manutencao_servicos_servico 
                            FOREIGN KEY (servico_id) 
                            REFERENCES servicos(id) 
                            ON DELETE SET NULL
                    )
                """)
                
                # Criar índices
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_manutencao_servicos_manutencao 
                    ON manutencao_servicos(manutencao_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_manutencao_servicos_servico 
                    ON manutencao_servicos(servico_id) WHERE servico_id IS NOT NULL
                """)
                
                # Criar trigger para updated_at
                cursor.execute("""
                    CREATE OR REPLACE FUNCTION update_manutencao_servicos_updated_at()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """)
                
                cursor.execute("""
                    DROP TRIGGER IF EXISTS trigger_manutencao_servicos_updated_at ON manutencao_servicos;
                    CREATE TRIGGER trigger_manutencao_servicos_updated_at
                        BEFORE UPDATE ON manutencao_servicos
                        FOR EACH ROW
                        EXECUTE FUNCTION update_manutencao_servicos_updated_at();
                """)
                
                print("   ✅ Tabela manutencao_servicos criada com sucesso")
            
            else:
                # SQLite
                print("   📝 Criando tabela manutencao_servicos (SQLite)...")
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS manutencao_servicos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        manutencao_id INTEGER NOT NULL,
                        servico_id INTEGER,
                        nome_servico TEXT NOT NULL,
                        descricao TEXT,
                        quantidade REAL DEFAULT 1.00 CHECK(quantidade > 0),
                        valor_unitario REAL DEFAULT 0.00 CHECK(valor_unitario >= 0),
                        subtotal REAL GENERATED ALWAYS AS (quantidade * valor_unitario) STORED,
                        observacoes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (manutencao_id) REFERENCES manutencoes(id) ON DELETE CASCADE,
                        FOREIGN KEY (servico_id) REFERENCES servicos(id) ON DELETE SET NULL
                    )
                """)
                
                # Criar índices
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_manutencao_servicos_manutencao 
                    ON manutencao_servicos(manutencao_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_manutencao_servicos_servico 
                    ON manutencao_servicos(servico_id)
                """)
                
                # Trigger para updated_at
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS trigger_manutencao_servicos_updated_at
                    AFTER UPDATE ON manutencao_servicos
                    FOR EACH ROW
                    BEGIN
                        UPDATE manutencao_servicos SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = NEW.id;
                    END;
                """)
                
                print("   ✅ Tabela manutencao_servicos criada com sucesso")
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao aplicar migração 005: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def down(self):
        """Reverter migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("   📝 Removendo tabela manutencao_servicos...")
            
            if self.is_postgres:
                # Remover trigger e function
                cursor.execute("DROP TRIGGER IF EXISTS trigger_manutencao_servicos_updated_at ON manutencao_servicos")
                cursor.execute("DROP FUNCTION IF EXISTS update_manutencao_servicos_updated_at()")
            
            # Remover tabela
            cursor.execute("DROP TABLE IF EXISTS manutencao_servicos CASCADE")
            
            conn.commit()
            print("   ✅ Tabela manutencao_servicos removida")
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao reverter migração 005: {e}")
        finally:
            cursor.close()
            conn.close()
