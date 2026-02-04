"""
Migração 006: Criar tabela ordens_servico
==========================================

OBJETIVO: Entidade técnica para gerenciar ordens de serviço

MUDANÇAS:
- Cria tabela ordens_servico vinculada a manutenções
- Suporta diferentes status (ORCAMENTO, APROVADO, EM_EXECUCAO, etc)
- FK para empresas, clientes e manutenções
- Multi-tenancy via empresa_id

REVERSÍVEL: Sim (DROP TABLE)
SEGURO PARA PRODUÇÃO: Sim (tabela nova, não afeta sistema existente)
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Cria tabela ordens_servico"""
    
    name = "Criar tabela ordens_servico"
    
    def up(self):
        """Aplicar migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.is_postgres:
                # PostgreSQL
                print("   📝 Criando tabela ordens_servico...")
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ordens_servico (
                        id BIGSERIAL PRIMARY KEY,
                        empresa_id BIGINT NOT NULL,
                        manutencao_id BIGINT NOT NULL,
                        cliente_id BIGINT NOT NULL,
                        numero_os VARCHAR(50) UNIQUE NOT NULL,
                        status VARCHAR(20) DEFAULT 'ORCAMENTO' 
                            CHECK(status IN ('RASCUNHO', 'ORCAMENTO', 'APROVADO', 
                                           'EM_EXECUCAO', 'FINALIZADO', 'FATURADO', 'CANCELADO')),
                        valor_mao_obra DECIMAL(10,2) DEFAULT 0.00 CHECK(valor_mao_obra >= 0),
                        valor_pecas DECIMAL(10,2) DEFAULT 0.00 CHECK(valor_pecas >= 0),
                        valor_servicos DECIMAL(10,2) DEFAULT 0.00 CHECK(valor_servicos >= 0),
                        valor_total DECIMAL(10,2) GENERATED ALWAYS AS 
                            (valor_mao_obra + valor_pecas + valor_servicos) STORED,
                        data_abertura TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        data_aprovacao TIMESTAMP WITH TIME ZONE,
                        data_conclusao TIMESTAMP WITH TIME ZONE,
                        data_faturamento TIMESTAMP WITH TIME ZONE,
                        observacoes TEXT,
                        observacoes_internas TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        
                        CONSTRAINT fk_ordens_servico_empresa 
                            FOREIGN KEY (empresa_id) 
                            REFERENCES empresas(id) 
                            ON DELETE RESTRICT,
                        
                        CONSTRAINT fk_ordens_servico_manutencao 
                            FOREIGN KEY (manutencao_id) 
                            REFERENCES manutencoes(id) 
                            ON DELETE RESTRICT,
                        
                        CONSTRAINT fk_ordens_servico_cliente 
                            FOREIGN KEY (cliente_id) 
                            REFERENCES clientes(id) 
                            ON DELETE RESTRICT,
                        
                        -- Garantir que cliente e empresa são compatíveis
                        CONSTRAINT check_cliente_mesma_empresa 
                            CHECK (
                                (SELECT empresa_id FROM clientes WHERE id = cliente_id) = empresa_id
                            )
                    )
                """)
                
                # Criar índices
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ordens_servico_empresa_id 
                    ON ordens_servico(empresa_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ordens_servico_empresa_status 
                    ON ordens_servico(empresa_id, status)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ordens_servico_cliente 
                    ON ordens_servico(cliente_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ordens_servico_manutencao 
                    ON ordens_servico(manutencao_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ordens_servico_numero 
                    ON ordens_servico(numero_os)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ordens_servico_data_abertura 
                    ON ordens_servico(empresa_id, data_abertura DESC)
                """)
                
                # Criar trigger para updated_at
                cursor.execute("""
                    CREATE OR REPLACE FUNCTION update_ordens_servico_updated_at()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """)
                
                cursor.execute("""
                    DROP TRIGGER IF EXISTS trigger_ordens_servico_updated_at ON ordens_servico;
                    CREATE TRIGGER trigger_ordens_servico_updated_at
                        BEFORE UPDATE ON ordens_servico
                        FOR EACH ROW
                        EXECUTE FUNCTION update_ordens_servico_updated_at();
                """)
                
                # Criar função para gerar número de OS automaticamente
                cursor.execute("""
                    CREATE OR REPLACE FUNCTION generate_numero_os()
                    RETURNS TRIGGER AS $$
                    DECLARE
                        next_number INTEGER;
                        ano_atual VARCHAR(4);
                    BEGIN
                        IF NEW.numero_os IS NULL OR NEW.numero_os = '' THEN
                            ano_atual := TO_CHAR(CURRENT_DATE, 'YYYY');
                            
                            SELECT COALESCE(MAX(
                                CAST(
                                    SUBSTRING(numero_os FROM POSITION('-' IN numero_os) + 1 FOR 
                                    POSITION('/' IN numero_os) - POSITION('-' IN numero_os) - 1)
                                AS INTEGER)
                            ), 0) + 1
                            INTO next_number
                            FROM ordens_servico
                            WHERE empresa_id = NEW.empresa_id 
                            AND numero_os LIKE 'OS-%/' || ano_atual;
                            
                            NEW.numero_os := 'OS-' || LPAD(next_number::TEXT, 6, '0') || '/' || ano_atual;
                        END IF;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """)
                
                cursor.execute("""
                    DROP TRIGGER IF EXISTS trigger_generate_numero_os ON ordens_servico;
                    CREATE TRIGGER trigger_generate_numero_os
                        BEFORE INSERT ON ordens_servico
                        FOR EACH ROW
                        EXECUTE FUNCTION generate_numero_os();
                """)
                
                print("   ✅ Tabela ordens_servico criada com sucesso")
            
            else:
                # SQLite
                print("   📝 Criando tabela ordens_servico (SQLite)...")
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ordens_servico (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        empresa_id INTEGER NOT NULL,
                        manutencao_id INTEGER NOT NULL,
                        cliente_id INTEGER NOT NULL,
                        numero_os TEXT UNIQUE NOT NULL,
                        status TEXT DEFAULT 'ORCAMENTO' 
                            CHECK(status IN ('RASCUNHO', 'ORCAMENTO', 'APROVADO', 
                                           'EM_EXECUCAO', 'FINALIZADO', 'FATURADO', 'CANCELADO')),
                        valor_mao_obra REAL DEFAULT 0.00 CHECK(valor_mao_obra >= 0),
                        valor_pecas REAL DEFAULT 0.00 CHECK(valor_pecas >= 0),
                        valor_servicos REAL DEFAULT 0.00 CHECK(valor_servicos >= 0),
                        valor_total REAL GENERATED ALWAYS AS 
                            (valor_mao_obra + valor_pecas + valor_servicos) STORED,
                        data_abertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        data_aprovacao TIMESTAMP,
                        data_conclusao TIMESTAMP,
                        data_faturamento TIMESTAMP,
                        observacoes TEXT,
                        observacoes_internas TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                        FOREIGN KEY (manutencao_id) REFERENCES manutencoes(id),
                        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
                    )
                """)
                
                # Criar índices
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ordens_servico_empresa_id 
                    ON ordens_servico(empresa_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ordens_servico_empresa_status 
                    ON ordens_servico(empresa_id, status)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ordens_servico_cliente 
                    ON ordens_servico(cliente_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ordens_servico_manutencao 
                    ON ordens_servico(manutencao_id)
                """)
                
                # Trigger para updated_at
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS trigger_ordens_servico_updated_at
                    AFTER UPDATE ON ordens_servico
                    FOR EACH ROW
                    BEGIN
                        UPDATE ordens_servico SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = NEW.id;
                    END;
                """)
                
                print("   ✅ Tabela ordens_servico criada com sucesso")
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao aplicar migração 006: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def down(self):
        """Reverter migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("   📝 Removendo tabela ordens_servico...")
            
            if self.is_postgres:
                # Remover triggers e functions
                cursor.execute("DROP TRIGGER IF EXISTS trigger_ordens_servico_updated_at ON ordens_servico")
                cursor.execute("DROP TRIGGER IF EXISTS trigger_generate_numero_os ON ordens_servico")
                cursor.execute("DROP FUNCTION IF EXISTS update_ordens_servico_updated_at()")
                cursor.execute("DROP FUNCTION IF EXISTS generate_numero_os()")
            
            # Remover tabela
            cursor.execute("DROP TABLE IF EXISTS ordens_servico CASCADE")
            
            conn.commit()
            print("   ✅ Tabela ordens_servico removida")
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao reverter migração 006: {e}")
        finally:
            cursor.close()
            conn.close()
