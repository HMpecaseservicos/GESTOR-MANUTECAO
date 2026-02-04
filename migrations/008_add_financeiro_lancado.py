"""
Migração 008: Adicionar campo financeiro_lancado_em em manutencoes
===================================================================

OBJETIVO: Garantir idempotência no lançamento financeiro automático

MUDANÇAS:
- Adiciona coluna financeiro_lancado_em em manutencoes
- Campo indica data/hora do lançamento financeiro
- NULL = ainda não lançado (permite verificação de idempotência)

REVERSÍVEL: Sim (DROP COLUMN)
SEGURO PARA PRODUÇÃO: Sim (ADD COLUMN nullable)
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Adiciona campo para controle de lançamento financeiro"""
    
    name = "Adicionar financeiro_lancado_em em manutencoes"
    
    def up(self):
        """Aplicar migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.is_postgres:
                # PostgreSQL
                print("   📝 Verificando se coluna financeiro_lancado_em existe...")
                
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'manutencoes' AND column_name = 'financeiro_lancado_em'
                """)
                
                if cursor.fetchone():
                    print("   ⚠️ Coluna financeiro_lancado_em já existe. Pulando...")
                else:
                    print("   📝 Adicionando coluna financeiro_lancado_em...")
                    cursor.execute("""
                        ALTER TABLE manutencoes 
                        ADD COLUMN financeiro_lancado_em TIMESTAMP WITH TIME ZONE DEFAULT NULL
                    """)
                    print("   ✅ Coluna adicionada com sucesso!")
                
                # Adicionar também tipo_lancamento para saber se foi ENTRADA ou DESPESA
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'manutencoes' AND column_name = 'financeiro_tipo'
                """)
                
                if cursor.fetchone():
                    print("   ⚠️ Coluna financeiro_tipo já existe. Pulando...")
                else:
                    print("   📝 Adicionando coluna financeiro_tipo...")
                    cursor.execute("""
                        ALTER TABLE manutencoes 
                        ADD COLUMN financeiro_tipo VARCHAR(20) DEFAULT NULL
                        CHECK (financeiro_tipo IN ('ENTRADA', 'DESPESA', NULL))
                    """)
                    print("   ✅ Coluna financeiro_tipo adicionada!")
                
                # Adicionar valor_total_servicos para SERVICO (soma dos serviços)
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'manutencoes' AND column_name = 'valor_total_servicos'
                """)
                
                if cursor.fetchone():
                    print("   ⚠️ Coluna valor_total_servicos já existe. Pulando...")
                else:
                    print("   📝 Adicionando coluna valor_total_servicos...")
                    cursor.execute("""
                        ALTER TABLE manutencoes 
                        ADD COLUMN valor_total_servicos DECIMAL(10,2) DEFAULT 0.00
                    """)
                    print("   ✅ Coluna valor_total_servicos adicionada!")
                
                conn.commit()
                
            else:
                # SQLite
                print("   📝 SQLite: verificando/adicionando colunas...")
                
                cursor.execute("PRAGMA table_info(manutencoes)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'financeiro_lancado_em' not in columns:
                    cursor.execute("ALTER TABLE manutencoes ADD COLUMN financeiro_lancado_em TEXT")
                
                if 'financeiro_tipo' not in columns:
                    cursor.execute("ALTER TABLE manutencoes ADD COLUMN financeiro_tipo TEXT")
                
                if 'valor_total_servicos' not in columns:
                    cursor.execute("ALTER TABLE manutencoes ADD COLUMN valor_total_servicos REAL DEFAULT 0.00")
                
                conn.commit()
            
            print("   ✅ Migração 008 aplicada com sucesso!")
            return True
            
        except Exception as e:
            print(f"   ❌ Erro na migração: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
    
    def down(self):
        """Reverter migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.is_postgres:
                cursor.execute("ALTER TABLE manutencoes DROP COLUMN IF EXISTS financeiro_lancado_em")
                cursor.execute("ALTER TABLE manutencoes DROP COLUMN IF EXISTS financeiro_tipo")
                cursor.execute("ALTER TABLE manutencoes DROP COLUMN IF EXISTS valor_total_servicos")
            else:
                print("   ⚠️ SQLite não suporta DROP COLUMN diretamente")
            
            conn.commit()
            print("   ✅ Migração 008 revertida!")
            return True
            
        except Exception as e:
            print(f"   ❌ Erro ao reverter: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
