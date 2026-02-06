"""
Migration 014: Adicionar campo unidade_medida na tabela veiculos
Para permitir escolher entre km (quilômetros) e hr (horas de trabalho)
Máquinas e equipamentos usam horas, veículos usam km
"""

def upgrade(cursor):
    """Adiciona coluna unidade_medida"""
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
    
    return True


def downgrade(cursor):
    """Remove coluna unidade_medida"""
    cursor.execute("""
        ALTER TABLE veiculos DROP COLUMN IF EXISTS unidade_medida
    """)
    return True
