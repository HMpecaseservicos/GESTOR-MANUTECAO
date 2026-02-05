"""
Migração 009: Adicionar cliente_id na tabela manutencoes
Para vincular manutenções/ordens de serviço a clientes
E permitir envio de orçamentos via WhatsApp
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Adicionar cliente_id em manutencoes para vincular ao cliente"""
    
    version = 9
    description = "Adicionar cliente_id na tabela manutencoes"
    
    def up(self):
        """Aplicar migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.is_postgres:
                print("   📝 Adicionando coluna cliente_id em manutencoes...")
                
                # Verificar se coluna já existe
                cursor.execute('''
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'manutencoes' AND column_name = 'cliente_id'
                ''')
                
                if not cursor.fetchone():
                    cursor.execute('''
                        ALTER TABLE manutencoes 
                        ADD COLUMN cliente_id BIGINT REFERENCES clientes(id) ON DELETE SET NULL
                    ''')
                    
                    # Criar índice para performance
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_manutencoes_cliente ON manutencoes(cliente_id)')
                    
                    print("   ✅ Coluna cliente_id adicionada com sucesso!")
                else:
                    print("   ⏭️ Coluna cliente_id já existe")
                
            else:
                # SQLite
                cursor.execute("PRAGMA table_info(manutencoes)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'cliente_id' not in columns:
                    cursor.execute('ALTER TABLE manutencoes ADD COLUMN cliente_id INTEGER')
                    print("   ✅ Coluna cliente_id adicionada com sucesso!")
                else:
                    print("   ⏭️ Coluna cliente_id já existe")
            
            conn.commit()
            
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
                cursor.execute('DROP INDEX IF EXISTS idx_manutencoes_cliente')
                cursor.execute('ALTER TABLE manutencoes DROP COLUMN IF EXISTS cliente_id')
            else:
                # SQLite não suporta DROP COLUMN facilmente
                pass
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
