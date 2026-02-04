"""
Migração 002: Criar tabela clientes
====================================

OBJETIVO: Criar tabela para gerenciar clientes (APENAS para empresas tipo SERVICO)

MUDANÇAS:
- Cria tabela clientes com todos os campos necessários
- Adiciona FK para empresas (multi-tenancy)
- Adiciona índices para performance
- Garante integridade com constraints

REVERSÍVEL: Sim (DROP TABLE)
SEGURO PARA PRODUÇÃO: Sim (tabela nova, não afeta sistema existente)
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Cria tabela clientes"""
    
    name = "Criar tabela clientes"
    
    def up(self):
        """Aplicar migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.is_postgres:
                # PostgreSQL
                print("   📝 Criando tabela clientes...")
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS clientes (
                        id BIGSERIAL PRIMARY KEY,
                        empresa_id BIGINT NOT NULL,
                        nome VARCHAR(200) NOT NULL,
                        documento VARCHAR(20),
                        tipo_documento VARCHAR(10) CHECK(tipo_documento IN ('CPF', 'CNPJ')),
                        telefone VARCHAR(20),
                        email VARCHAR(200),
                        endereco TEXT,
                        cidade VARCHAR(100),
                        estado VARCHAR(2),
                        cep VARCHAR(10),
                        observacoes TEXT,
                        status VARCHAR(20) DEFAULT 'ATIVO' CHECK(status IN ('ATIVO', 'INATIVO')),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        
                        CONSTRAINT fk_clientes_empresa 
                            FOREIGN KEY (empresa_id) 
                            REFERENCES empresas(id) 
                            ON DELETE RESTRICT,
                        
                        CONSTRAINT unique_documento_por_empresa 
                            UNIQUE(empresa_id, documento)
                    )
                """)
                
                # Criar índices
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_clientes_empresa_id 
                    ON clientes(empresa_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_clientes_empresa_status 
                    ON clientes(empresa_id, status)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_clientes_documento 
                    ON clientes(documento) WHERE documento IS NOT NULL
                """)
                
                # Criar trigger para updated_at
                cursor.execute("""
                    CREATE OR REPLACE FUNCTION update_clientes_updated_at()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """)
                
                cursor.execute("""
                    DROP TRIGGER IF EXISTS trigger_clientes_updated_at ON clientes;
                    CREATE TRIGGER trigger_clientes_updated_at
                        BEFORE UPDATE ON clientes
                        FOR EACH ROW
                        EXECUTE FUNCTION update_clientes_updated_at();
                """)
                
                print("   ✅ Tabela clientes criada com sucesso")
            
            else:
                # SQLite
                print("   📝 Criando tabela clientes (SQLite)...")
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS clientes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        empresa_id INTEGER NOT NULL,
                        nome TEXT NOT NULL,
                        documento TEXT,
                        tipo_documento TEXT CHECK(tipo_documento IN ('CPF', 'CNPJ')),
                        telefone TEXT,
                        email TEXT,
                        endereco TEXT,
                        cidade TEXT,
                        estado TEXT,
                        cep TEXT,
                        observacoes TEXT,
                        status TEXT DEFAULT 'ATIVO' CHECK(status IN ('ATIVO', 'INATIVO')),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                        UNIQUE(empresa_id, documento)
                    )
                """)
                
                # Criar índices
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_clientes_empresa_id 
                    ON clientes(empresa_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_clientes_empresa_status 
                    ON clientes(empresa_id, status)
                """)
                
                # Trigger para updated_at
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS trigger_clientes_updated_at
                    AFTER UPDATE ON clientes
                    FOR EACH ROW
                    BEGIN
                        UPDATE clientes SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = NEW.id;
                    END;
                """)
                
                print("   ✅ Tabela clientes criada com sucesso")
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao aplicar migração 002: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def down(self):
        """Reverter migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("   📝 Removendo tabela clientes...")
            
            if self.is_postgres:
                # Remover trigger e function
                cursor.execute("DROP TRIGGER IF EXISTS trigger_clientes_updated_at ON clientes")
                cursor.execute("DROP FUNCTION IF EXISTS update_clientes_updated_at()")
            
            # Remover tabela
            cursor.execute("DROP TABLE IF EXISTS clientes CASCADE")
            
            conn.commit()
            print("   ✅ Tabela clientes removida")
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao reverter migração 002: {e}")
        finally:
            cursor.close()
            conn.close()
