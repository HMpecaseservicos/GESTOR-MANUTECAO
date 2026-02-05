#!/usr/bin/env python3
"""Script para criar usuário de teste"""

import os
import sys

# Adicionar path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

def criar_usuario_teste():
    if not Config.IS_POSTGRES:
        print("Este script só funciona com PostgreSQL")
        return
    
    import psycopg2
    
    senha_hash = bcrypt.generate_password_hash('teste123').decode('utf-8')
    
    conn = psycopg2.connect(Config.DATABASE_URL)
    cur = conn.cursor()
    
    try:
        # Verificar se empresa existe
        cur.execute('SELECT id FROM empresas LIMIT 1')
        empresa = cur.fetchone()
        
        if not empresa:
            # Criar empresa
            cur.execute("""
                INSERT INTO empresas (nome, tipo_operacao, plano, limite_veiculos, limite_usuarios, limite_clientes, ativo)
                VALUES ('Empresa Demo', 'SERVICO', 'PRO', 50, 5, 100, true)
                RETURNING id
            """)
            empresa_id = cur.fetchone()[0]
            print(f'✅ Empresa criada com ID: {empresa_id}')
        else:
            empresa_id = empresa[0]
            print(f'ℹ️ Empresa existente com ID: {empresa_id}')
        
        # Verificar se usuario existe
        cur.execute("SELECT id FROM usuarios WHERE username = 'admin'")
        user = cur.fetchone()
        
        if not user:
            # Criar usuario admin
            cur.execute("""
                INSERT INTO usuarios (empresa_id, username, nome, email, password_hash, role, ativo)
                VALUES (%s, 'admin', 'Administrador', 'admin@demo.com', %s, 'ADMIN', true)
                RETURNING id
            """, (empresa_id, senha_hash))
            user_id = cur.fetchone()[0]
            print(f'✅ Usuário admin criado com ID: {user_id}')
        else:
            # Atualizar senha
            cur.execute("UPDATE usuarios SET password_hash = %s WHERE username = 'admin'", (senha_hash,))
            print(f'ℹ️ Senha do usuário admin atualizada')
        
        conn.commit()
        print('')
        print('=' * 50)
        print('CREDENCIAIS DE ACESSO')
        print('=' * 50)
        print('URL: https://gestor-frota-hibrido.fly.dev')
        print('Usuário: admin')
        print('Senha: teste123')
        print('=' * 50)
        
    except Exception as e:
        print(f'❌ Erro: {e}')
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    criar_usuario_teste()
