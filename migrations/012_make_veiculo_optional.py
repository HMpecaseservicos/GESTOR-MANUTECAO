"""
Migration 012: Tornar veiculo_id opcional em manutencoes
Para modo SERVIÇO, veículos são opcionais (muitos serviços são em implementos, não veículos)
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Tornar veiculo_id opcional para modo SERVICO"""
    
    name = "Tornar veiculo_id opcional em manutencoes"
    
    def up(self):
        """Aplicar migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("   📝 Alterando veiculo_id para permitir NULL...")
            
            cursor.execute('''
                ALTER TABLE manutencoes 
                ALTER COLUMN veiculo_id DROP NOT NULL
            ''')
            
            conn.commit()
            print("   ✅ veiculo_id agora é opcional")
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def down(self):
        """Reverter migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Primeiro, atualizar registros NULL para um valor padrão
            cursor.execute('''
                UPDATE manutencoes SET veiculo_id = (
                    SELECT id FROM veiculos WHERE empresa_id = manutencoes.empresa_id LIMIT 1
                ) WHERE veiculo_id IS NULL
            ''')
            
            cursor.execute('''
                ALTER TABLE manutencoes 
                ALTER COLUMN veiculo_id SET NOT NULL
            ''')
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
