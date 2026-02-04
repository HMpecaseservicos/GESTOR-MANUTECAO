# PostgreSQL Migrations

Este diretório contém as migrações do banco de dados PostgreSQL para preparar o sistema para o modelo híbrido (FROTA + SERVIÇO).

## Estrutura

- `__init__.py` - Módulo de inicialização
- `migration_manager.py` - Gerenciador de migrações
- `001_add_tipo_operacao_empresas.py` - Adiciona campo tipo_operacao na tabela empresas
- `002_create_clientes.py` - Cria tabela clientes
- `003_create_servicos.py` - Cria tabela servicos (catálogo interno)
- `004_add_cliente_id_veiculos.py` - Adiciona cliente_id na tabela veiculos
- `005_create_manutencao_servicos.py` - Cria tabela manutencao_servicos
- `006_create_ordens_servico.py` - Cria tabela ordens_servico
- `007_create_indexes.py` - Cria índices de performance

## Como usar

```python
from migrations.migration_manager import MigrationManager

manager = MigrationManager(database_url)
manager.run_pending_migrations()
```

## Rollback

Cada migração tem um método `down()` para reverter as mudanças se necessário.
