"""
Migration 012: Tornar veiculo_id opcional em manutencoes
Para modo SERVIÇO, veículos são opcionais (muitos serviços são em implementos, não veículos)
"""

def upgrade(cursor, placeholder='%s'):
    """Tornar veiculo_id nullable"""
    print("Alterando veiculo_id para permitir NULL...")
    
    # PostgreSQL syntax para alterar constraint
    cursor.execute('''
        ALTER TABLE manutencoes 
        ALTER COLUMN veiculo_id DROP NOT NULL
    ''')
    
    print("✅ veiculo_id agora é opcional")

def downgrade(cursor, placeholder='%s'):
    """Reverter - tornar veiculo_id obrigatório novamente"""
    # Primeiro, atualizar registros NULL para um valor padrão
    cursor.execute(f'''
        UPDATE manutencoes SET veiculo_id = (
            SELECT id FROM veiculos WHERE empresa_id = manutencoes.empresa_id LIMIT 1
        ) WHERE veiculo_id IS NULL
    ''')
    
    cursor.execute('''
        ALTER TABLE manutencoes 
        ALTER COLUMN veiculo_id SET NOT NULL
    ''')
