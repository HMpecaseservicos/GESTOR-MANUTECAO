"""
Migração 003: Criar tabela servicos (catálogo interno)
=======================================================

OBJETIVO: Criar catálogo interno de serviços por empresa

MUDANÇAS:
- Cria tabela servicos para catálogo interno de cada empresa
- Permite reuso de serviços em múltiplas manutenções
- Servicos podem ser criados "on-the-fly" dentro da manutenção
- Multi-tenancy via empresa_id

REVERSÍVEL: Sim (DROP TABLE)
SEGURO PARA PRODUÇÃO: Sim (tabela nova, não afeta sistema existente)
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Cria tabela servicos"""
    
    name = "Criar tabela servicos (catálogo interno)"
    
    def up(self):
        """Aplicar migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.is_postgres:
                # PostgreSQL
                print("   📝 Criando tabela servicos...")
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS servicos (
                        id BIGSERIAL PRIMARY KEY,
                        empresa_id BIGINT NOT NULL,
                        nome VARCHAR(200) NOT NULL,
                        descricao TEXT,
                        preco_base DECIMAL(10,2) DEFAULT 0.00 CHECK(preco_base >= 0),
                        tempo_estimado_minutos INTEGER,
                        categoria VARCHAR(100),
                        ativo BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        
                        CONSTRAINT fk_servicos_empresa 
                            FOREIGN KEY (empresa_id) 
                            REFERENCES empresas(id) 
                            ON DELETE RESTRICT
                    )
                """)
                
                # Criar índices
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_servicos_empresa_id 
                    ON servicos(empresa_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_servicos_empresa_ativo 
                    ON servicos(empresa_id, ativo)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_servicos_categoria 
                    ON servicos(empresa_id, categoria) WHERE categoria IS NOT NULL
                """)
                
                # Criar trigger para updated_at
                cursor.execute("""
                    CREATE OR REPLACE FUNCTION update_servicos_updated_at()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """)
                
                cursor.execute("""
                    DROP TRIGGER IF EXISTS trigger_servicos_updated_at ON servicos;
                    CREATE TRIGGER trigger_servicos_updated_at
                        BEFORE UPDATE ON servicos
                        FOR EACH ROW
                        EXECUTE FUNCTION update_servicos_updated_at();
                """)
                
                print("   ✅ Tabela servicos criada com sucesso")
            
            else:
                # SQLite
                print("   📝 Criando tabela servicos (SQLite)...")
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS servicos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        empresa_id INTEGER NOT NULL,
                        nome TEXT NOT NULL,
                        descricao TEXT,
                        preco_base REAL DEFAULT 0.00 CHECK(preco_base >= 0),
                        tempo_estimado_minutos INTEGER,
                        categoria TEXT,
                        ativo BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
                    )
                """)
                
                # Criar índices
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_servicos_empresa_id 
                    ON servicos(empresa_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_servicos_empresa_ativo 
                    ON servicos(empresa_id, ativo)
                """)
                
                # Trigger para updated_at
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS trigger_servicos_updated_at
                    AFTER UPDATE ON servicos
                    FOR EACH ROW
                    BEGIN
                        UPDATE servicos SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = NEW.id;
                    END;
                """)
                
                print("   ✅ Tabela servicos criada com sucesso")
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao aplicar migração 003: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def down(self):
        """Reverter migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("   📝 Removendo tabela servicos...")
            
            if self.is_postgres:
                # Remover trigger e function
                cursor.execute("DROP TRIGGER IF EXISTS trigger_servicos_updated_at ON servicos")
                cursor.execute("DROP FUNCTION IF EXISTS update_servicos_updated_at()")
            
            # Remover tabela
            cursor.execute("DROP TABLE IF EXISTS servicos CASCADE")
            
            conn.commit()
            print("   ✅ Tabela servicos removida")
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao reverter migração 003: {e}")
        finally:
            cursor.close()
            conn.close()
