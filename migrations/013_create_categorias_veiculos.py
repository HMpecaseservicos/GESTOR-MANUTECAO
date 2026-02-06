"""
Migration 013: Criar tabela de categorias de veículos/equipamentos
Permite que cada empresa personalize suas próprias categorias
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Criar tabela de categorias de veículos personalizáveis"""
    
    name = "Criar categorias de veículos personalizáveis"
    
    def up(self):
        """Aplicar migração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("   📝 Criando tabela categorias_veiculos...")
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categorias_veiculos (
                    id SERIAL PRIMARY KEY,
                    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                    nome VARCHAR(100) NOT NULL,
                    icone VARCHAR(50) DEFAULT 'fa-cube',
                    cor VARCHAR(20) DEFAULT 'secondary',
                    grupo VARCHAR(50) DEFAULT 'Equipamento',
                    ativo BOOLEAN DEFAULT true,
                    ordem INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Criar índice para performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_categorias_veiculos_empresa 
                ON categorias_veiculos(empresa_id, ativo)
            ''')
            
            conn.commit()
            print("   ✅ Tabela categorias_veiculos criada com sucesso")
            
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
            cursor.execute('DROP TABLE IF EXISTS categorias_veiculos CASCADE')
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
