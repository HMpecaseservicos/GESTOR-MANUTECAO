#!/usr/bin/env python3
"""
Script para inicializar o banco de dados
"""

try:
    from app import init_db
    init_db()
    print("✅ Banco inicializado com sucesso!")
    
    # Verificar se as tabelas foram criadas
    import sqlite3
    conn = sqlite3.connect('database/frota.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tabelas criadas: {[table[0] for table in tables]}")
    
    # Verificar dados de exemplo
    cursor.execute("SELECT COUNT(*) FROM veiculos")
    veiculos = cursor.fetchone()[0]
    print(f"Veículos inseridos: {veiculos}")
    
    cursor.execute("SELECT COUNT(*) FROM pecas")
    pecas = cursor.fetchone()[0]
    print(f"Peças inseridas: {pecas}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()