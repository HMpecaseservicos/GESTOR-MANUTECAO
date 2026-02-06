"""
Migration 014: Adicionar campo unidade_medida na tabela veiculos
Para permitir escolher entre km (quilômetros) e hr (horas de trabalho)
Máquinas e equipamentos usam horas, veículos usam km
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Adicionar campo unidade_medida para km/hr"""
    
    name = "Adicionar unidade de medida (km/hr) nos veículos"
    
    def up(self):
        """Aplicar migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("   📝 Adicionando coluna unidade_medida em veiculos...")
            
            # Verificar se coluna já existe
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'veiculos' AND column_name = 'unidade_medida'
            """)
            
            if not cursor.fetchone():
                cursor.execute("""
                    ALTER TABLE veiculos 
                    ADD COLUMN unidade_medida VARCHAR(10) DEFAULT 'km'
                """)
                print("   ✅ Coluna unidade_medida adicionada")
                
                # Atualizar registros existentes baseado no tipo
                cursor.execute("""
                    UPDATE veiculos 
                    SET unidade_medida = 'hr'
                    WHERE LOWER(tipo) IN ('máquina', 'maquina', 'equipamento', 'prensa', 
                                          'compressor', 'gerador', 'bomba', 'empilhadeira',
                                          'guincho', 'implemento', 'ferramenta')
                """)
                print("   ✅ Unidades atualizadas para equipamentos existentes")
            else:
                print("   ⏭️ Coluna unidade_medida já existe")
            
            conn.commit()
            
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
            cursor.execute("""
                ALTER TABLE veiculos DROP COLUMN IF EXISTS unidade_medida
            """)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
