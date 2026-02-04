"""
Migração 001: Adicionar tipo_operacao na tabela empresas
=========================================================

OBJETIVO: Preparar a tabela empresas para o modelo híbrido (FROTA + SERVIÇO)

MUDANÇAS:
- Adiciona coluna tipo_operacao VARCHAR(10) com valores 'FROTA' ou 'SERVICO'
- Define 'FROTA' como padrão para manter compatibilidade
- Adiciona constraint CHECK para validar valores
- Adiciona índice para performance

REVERSÍVEL: Sim
SEGURO PARA PRODUÇÃO: Sim (não quebra sistema existente)
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Adiciona tipo_operacao na tabela empresas"""
    
    name = "Adicionar tipo_operacao em empresas"
    
    def up(self):
        """Aplicar migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.is_postgres:
                # PostgreSQL
                print("   📝 Adicionando coluna tipo_operacao...")
                
                # Verificar se coluna já existe
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='empresas' AND column_name='tipo_operacao'
                """)
                
                if not cursor.fetchone():
                    # Adicionar coluna com default temporário
                    cursor.execute("""
                        ALTER TABLE empresas 
                        ADD COLUMN tipo_operacao VARCHAR(10) DEFAULT 'FROTA'
                    """)
                    
                    # Adicionar constraint CHECK
                    cursor.execute("""
                        ALTER TABLE empresas
                        ADD CONSTRAINT check_tipo_operacao 
                        CHECK (tipo_operacao IN ('FROTA', 'SERVICO'))
                    """)
                    
                    # Tornar NOT NULL após popular com default
                    cursor.execute("""
                        ALTER TABLE empresas 
                        ALTER COLUMN tipo_operacao SET NOT NULL
                    """)
                    
                    # Criar índice para performance
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_empresas_tipo_operacao 
                        ON empresas(tipo_operacao)
                    """)
                    
                    print("   ✅ Coluna tipo_operacao adicionada com sucesso")
                else:
                    print("   ℹ️  Coluna tipo_operacao já existe")
            
            else:
                # SQLite
                print("   📝 Adicionando coluna tipo_operacao (SQLite)...")
                
                # Verificar se coluna já existe
                cursor.execute("PRAGMA table_info(empresas)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'tipo_operacao' not in columns:
                    # SQLite não suporta ALTER TABLE com CHECK, então fazemos mais simples
                    cursor.execute("""
                        ALTER TABLE empresas 
                        ADD COLUMN tipo_operacao TEXT DEFAULT 'FROTA' NOT NULL 
                        CHECK(tipo_operacao IN ('FROTA', 'SERVICO'))
                    """)
                    
                    # Criar índice
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_empresas_tipo_operacao 
                        ON empresas(tipo_operacao)
                    """)
                    
                    print("   ✅ Coluna tipo_operacao adicionada com sucesso")
                else:
                    print("   ℹ️  Coluna tipo_operacao já existe")
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao aplicar migração 001: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def down(self):
        """Reverter migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.is_postgres:
                print("   📝 Removendo coluna tipo_operacao...")
                
                # Remover constraint
                cursor.execute("""
                    ALTER TABLE empresas 
                    DROP CONSTRAINT IF EXISTS check_tipo_operacao
                """)
                
                # Remover índice
                cursor.execute("DROP INDEX IF EXISTS idx_empresas_tipo_operacao")
                
                # Remover coluna
                cursor.execute("ALTER TABLE empresas DROP COLUMN IF EXISTS tipo_operacao")
                
                print("   ✅ Coluna tipo_operacao removida")
            
            else:
                # SQLite não suporta DROP COLUMN facilmente
                print("   ⚠️  SQLite: não é possível remover coluna facilmente")
                print("   ℹ️  Mantenha a coluna ou recrie a tabela manualmente")
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao reverter migração 001: {e}")
        finally:
            cursor.close()
            conn.close()
