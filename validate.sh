#!/bin/bash
# Script para validar migrações no Fly.io

echo "==================================="
echo "VALIDAÇÃO ETAPA 0 - FLY.IO"
echo "==================================="

# 1. Verificar se tabela de migrações existe
python3 -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute(\"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema='public' AND table_name='schema_migrations')\")
exists = cur.fetchone()[0]
print(f'Tabela schema_migrations existe: {exists}')
if exists:
    cur.execute('SELECT COUNT(*) FROM schema_migrations WHERE success=true')
    count = cur.fetchone()[0]
    print(f'Migrações aplicadas com sucesso: {count}/7')
    cur.execute('SELECT version, name FROM schema_migrations ORDER BY version')
    for v, n in cur.fetchall():
        print(f'  - {v}: {n}')
conn.close()
"

# 2. Verificar novas tabelas
python3 -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
tables = ['clientes', 'servicos', 'manutencao_servicos', 'ordens_servico']
cur.execute(\"SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name = ANY(%s)\", (tables,))
found = [t[0] for t in cur.fetchall()]
print(f'Novas tabelas encontradas: {len(found)}/{len(tables)}')
for t in found:
    print(f'  ✓ {t}')
conn.close()
"

# 3. Verificar colunas adicionadas
python3 -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute(\"SELECT column_name FROM information_schema.columns WHERE table_name='empresas' AND column_name='tipo_operacao'\")
if cur.fetchone():
    print('✓ empresas.tipo_operacao adicionada')
cur.execute(\"SELECT column_name FROM information_schema.columns WHERE table_name='veiculos' AND column_name='cliente_id'\")
if cur.fetchone():
    print('✓ veiculos.cliente_id adicionada')
conn.close()
"

echo "==================================="
echo "VALIDAÇÃO COMPLETA"
echo "==================================="
