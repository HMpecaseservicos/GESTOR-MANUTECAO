"""
Script para atualizar a tabela manutencoes adicionando as colunas que faltam
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'database', 'frota.db')

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Verificando colunas da tabela manutencoes...")
    cursor.execute('PRAGMA table_info(manutencoes)')
    colunas = [row[1] for row in cursor.fetchall()]
    print(f"Colunas existentes: {colunas}")
    
    colunas_adicionar = []
    
    if 'custo_mao_obra' not in colunas:
        colunas_adicionar.append(('custo_mao_obra', 'REAL DEFAULT 0'))
    
    if 'custo_total' not in colunas:
        colunas_adicionar.append(('custo_total', 'REAL DEFAULT 0'))
    
    if 'data_criacao' not in colunas:
        colunas_adicionar.append(('data_criacao', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'))
    
    if 'observacoes' not in colunas:
        colunas_adicionar.append(('observacoes', 'TEXT'))
    
    if 'km_veiculo' not in colunas:
        colunas_adicionar.append(('km_veiculo', 'INTEGER'))
    
    if colunas_adicionar:
        print(f"\nAdicionando {len(colunas_adicionar)} colunas...")
        for coluna, tipo in colunas_adicionar:
            try:
                cursor.execute(f'ALTER TABLE manutencoes ADD COLUMN {coluna} {tipo}')
                print(f"✅ Coluna '{coluna}' adicionada com sucesso!")
            except sqlite3.OperationalError as e:
                print(f"⚠️ Erro ao adicionar coluna '{coluna}': {e}")
        
        conn.commit()
        print("\n✅ Tabela atualizada com sucesso!")
    else:
        print("\n✅ Todas as colunas já existem!")
    
    # Verificar novamente
    print("\nVerificando colunas após atualização...")
    cursor.execute('PRAGMA table_info(manutencoes)')
    colunas_final = [(row[1], row[2]) for row in cursor.fetchall()]
    for col, tipo in colunas_final:
        print(f"  - {col}: {tipo}")
    
    conn.close()
    print("\n🎉 Atualização concluída!")
    
except Exception as e:
    print(f"❌ Erro: {e}")
