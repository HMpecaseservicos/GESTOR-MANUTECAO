"""
Migração 000: Bootstrap do Schema Base
======================================

OBJETIVO: Criar TODAS as tabelas base do sistema para PostgreSQL.
Esta migração representa o estado inicial do sistema antes das evoluções híbridas.

MUDANÇAS:
- Cria tabela empresas (base multi-tenancy)
- Cria tabela usuarios (autenticação)
- Cria tabela logs_acoes (auditoria)
- Cria tabela veiculos
- Cria tabela fornecedores
- Cria tabela pecas
- Cria tabela manutencoes
- Cria tabela manutencao_pecas
- Cria tabela historico_estoque
- Cria tabela tecnicos
- Cria índices para performance

REVERSÍVEL: Sim (DROP ALL TABLES)
SEGURO PARA PRODUÇÃO: Sim (apenas cria estrutura, não insere dados)

IMPORTANTE: Esta migração DEVE ser a primeira a rodar (versão 000).
            As migrações posteriores (001+) dependem destas tabelas.
"""

from migrations.migration_manager import BaseMigration


class Migration(BaseMigration):
    """Bootstrap do schema base do sistema"""
    
    name = "Bootstrap do schema base (PostgreSQL)"
    
    def up(self):
        """Aplicar migração - criar todas as tabelas base"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.is_postgres:
                self._create_postgres_schema(cursor)
            else:
                self._create_sqlite_schema(cursor)
            
            conn.commit()
            print("   ✅ Schema base criado com sucesso!")
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao criar schema base: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def _create_postgres_schema(self, cursor):
        """Criar schema para PostgreSQL"""
        
        # =============================================
        # 1. TABELA EMPRESAS (BASE MULTI-TENANCY)
        # =============================================
        print("   📝 Criando tabela empresas...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS empresas (
                id BIGSERIAL PRIMARY KEY,
                nome VARCHAR(200) NOT NULL,
                nome_fantasia VARCHAR(200),
                cnpj VARCHAR(20) UNIQUE,
                telefone VARCHAR(20),
                email VARCHAR(200),
                endereco TEXT,
                cidade VARCHAR(100),
                estado VARCHAR(2),
                cep VARCHAR(10),
                plano VARCHAR(50) DEFAULT 'basico',
                limite_veiculos INTEGER DEFAULT 10,
                limite_usuarios INTEGER DEFAULT 3,
                ativo BOOLEAN DEFAULT TRUE,
                data_criacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # =============================================
        # 2. TABELA USUARIOS (AUTENTICAÇÃO)
        # =============================================
        print("   📝 Criando tabela usuarios...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id BIGSERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(200),
                nome VARCHAR(200),
                telefone VARCHAR(20),
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'usuario',
                empresa_id BIGINT,
                ativo BOOLEAN DEFAULT TRUE,
                data_criacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                ultimo_login TIMESTAMP WITH TIME ZONE,
                
                CONSTRAINT fk_usuarios_empresa
                    FOREIGN KEY (empresa_id) 
                    REFERENCES empresas(id) 
                    ON DELETE SET NULL
            )
        """)
        
        # =============================================
        # 3. TABELA LOGS_ACOES (AUDITORIA)
        # =============================================
        print("   📝 Criando tabela logs_acoes...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs_acoes (
                id BIGSERIAL PRIMARY KEY,
                usuario_id BIGINT,
                acao VARCHAR(200),
                detalhes TEXT,
                ip_address VARCHAR(50),
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                
                CONSTRAINT fk_logs_usuario
                    FOREIGN KEY (usuario_id) 
                    REFERENCES usuarios(id) 
                    ON DELETE SET NULL
            )
        """)
        
        # =============================================
        # 4. TABELA VEICULOS
        # =============================================
        print("   📝 Criando tabela veiculos...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS veiculos (
                id BIGSERIAL PRIMARY KEY,
                empresa_id BIGINT NOT NULL,
                tipo VARCHAR(50) NOT NULL,
                marca VARCHAR(100) NOT NULL,
                modelo VARCHAR(100) NOT NULL,
                placa VARCHAR(20) NOT NULL,
                ano INTEGER,
                quilometragem INTEGER DEFAULT 0,
                proxima_manutencao DATE,
                status VARCHAR(50) DEFAULT 'Operacional',
                observacoes TEXT,
                data_cadastro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                
                CONSTRAINT fk_veiculos_empresa
                    FOREIGN KEY (empresa_id) 
                    REFERENCES empresas(id) 
                    ON DELETE CASCADE,
                
                CONSTRAINT unique_placa_empresa
                    UNIQUE(empresa_id, placa)
            )
        """)
        
        # =============================================
        # 5. TABELA FORNECEDORES
        # =============================================
        print("   📝 Criando tabela fornecedores...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fornecedores (
                id BIGSERIAL PRIMARY KEY,
                empresa_id BIGINT NOT NULL,
                nome VARCHAR(200) NOT NULL,
                contato VARCHAR(200),
                telefone VARCHAR(20),
                email VARCHAR(200),
                endereco TEXT,
                cnpj VARCHAR(20),
                especialidade VARCHAR(200),
                ativo BOOLEAN DEFAULT TRUE,
                data_cadastro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                
                CONSTRAINT fk_fornecedores_empresa
                    FOREIGN KEY (empresa_id) 
                    REFERENCES empresas(id) 
                    ON DELETE CASCADE
            )
        """)
        
        # =============================================
        # 6. TABELA PECAS
        # =============================================
        print("   📝 Criando tabela pecas...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pecas (
                id BIGSERIAL PRIMARY KEY,
                empresa_id BIGINT NOT NULL,
                nome VARCHAR(200) NOT NULL,
                codigo VARCHAR(100) NOT NULL,
                descricao TEXT,
                veiculo_compativel VARCHAR(200) DEFAULT 'Universal',
                preco NUMERIC(12, 2) NOT NULL DEFAULT 0,
                fornecedor_id BIGINT,
                quantidade_estoque INTEGER DEFAULT 0,
                estoque_minimo INTEGER DEFAULT 5,
                unidade VARCHAR(20) DEFAULT 'UN',
                ativo BOOLEAN DEFAULT TRUE,
                data_cadastro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                
                CONSTRAINT fk_pecas_empresa
                    FOREIGN KEY (empresa_id) 
                    REFERENCES empresas(id) 
                    ON DELETE CASCADE,
                
                CONSTRAINT fk_pecas_fornecedor
                    FOREIGN KEY (fornecedor_id) 
                    REFERENCES fornecedores(id) 
                    ON DELETE SET NULL,
                
                CONSTRAINT unique_codigo_empresa
                    UNIQUE(empresa_id, codigo),
                
                CONSTRAINT check_preco_positivo
                    CHECK (preco >= 0),
                
                CONSTRAINT check_estoque_positivo
                    CHECK (quantidade_estoque >= 0)
            )
        """)
        
        # =============================================
        # 7. TABELA MANUTENCOES
        # =============================================
        print("   📝 Criando tabela manutencoes...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manutencoes (
                id BIGSERIAL PRIMARY KEY,
                empresa_id BIGINT NOT NULL,
                veiculo_id BIGINT NOT NULL,
                tipo VARCHAR(50) NOT NULL,
                descricao TEXT,
                data_agendada DATE NOT NULL,
                data_realizada DATE,
                data_criacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                custo_mao_obra NUMERIC(12, 2) DEFAULT 0,
                custo_total NUMERIC(12, 2) DEFAULT 0,
                status VARCHAR(50) DEFAULT 'Agendada',
                tecnico VARCHAR(200),
                observacoes TEXT,
                km_veiculo INTEGER,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                
                CONSTRAINT fk_manutencoes_empresa
                    FOREIGN KEY (empresa_id) 
                    REFERENCES empresas(id) 
                    ON DELETE CASCADE,
                
                CONSTRAINT fk_manutencoes_veiculo
                    FOREIGN KEY (veiculo_id) 
                    REFERENCES veiculos(id) 
                    ON DELETE CASCADE
            )
        """)
        
        # =============================================
        # 8. TABELA MANUTENCAO_PECAS
        # =============================================
        print("   📝 Criando tabela manutencao_pecas...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manutencao_pecas (
                id BIGSERIAL PRIMARY KEY,
                manutencao_id BIGINT NOT NULL,
                peca_id BIGINT NOT NULL,
                quantidade INTEGER NOT NULL DEFAULT 1,
                preco_unitario NUMERIC(12, 2) NOT NULL DEFAULT 0,
                subtotal NUMERIC(12, 2) GENERATED ALWAYS AS (quantidade * preco_unitario) STORED,
                data_adicao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                observacoes TEXT,
                
                CONSTRAINT fk_manutencao_pecas_manutencao
                    FOREIGN KEY (manutencao_id) 
                    REFERENCES manutencoes(id) 
                    ON DELETE CASCADE,
                
                CONSTRAINT fk_manutencao_pecas_peca
                    FOREIGN KEY (peca_id) 
                    REFERENCES pecas(id) 
                    ON DELETE RESTRICT,
                
                CONSTRAINT check_quantidade_positiva
                    CHECK (quantidade > 0),
                
                CONSTRAINT check_preco_unitario_positivo
                    CHECK (preco_unitario >= 0)
            )
        """)
        
        # =============================================
        # 9. TABELA HISTORICO_ESTOQUE
        # =============================================
        print("   📝 Criando tabela historico_estoque...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_estoque (
                id BIGSERIAL PRIMARY KEY,
                peca_id BIGINT NOT NULL,
                operacao VARCHAR(20) NOT NULL,
                quantidade_anterior INTEGER NOT NULL,
                quantidade_movimento INTEGER NOT NULL,
                quantidade_nova INTEGER NOT NULL,
                motivo TEXT,
                usuario VARCHAR(200) DEFAULT 'Sistema',
                data_operacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                manutencao_id BIGINT,
                
                CONSTRAINT fk_historico_peca
                    FOREIGN KEY (peca_id) 
                    REFERENCES pecas(id) 
                    ON DELETE CASCADE,
                
                CONSTRAINT fk_historico_manutencao
                    FOREIGN KEY (manutencao_id) 
                    REFERENCES manutencoes(id) 
                    ON DELETE SET NULL,
                
                CONSTRAINT check_operacao_valida
                    CHECK (operacao IN ('ENTRADA', 'SAIDA', 'AJUSTE'))
            )
        """)
        
        # =============================================
        # 10. TABELA TECNICOS
        # =============================================
        print("   📝 Criando tabela tecnicos...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tecnicos (
                id BIGSERIAL PRIMARY KEY,
                empresa_id BIGINT NOT NULL,
                nome VARCHAR(200) NOT NULL,
                cpf VARCHAR(20),
                telefone VARCHAR(20),
                email VARCHAR(200),
                especialidade VARCHAR(200),
                data_admissao DATE,
                status VARCHAR(50) DEFAULT 'Ativo',
                data_cadastro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                
                CONSTRAINT fk_tecnicos_empresa
                    FOREIGN KEY (empresa_id) 
                    REFERENCES empresas(id) 
                    ON DELETE CASCADE
            )
        """)
        
        # =============================================
        # ÍNDICES PARA PERFORMANCE
        # =============================================
        print("   📝 Criando índices...")
        
        # Índices de empresas
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_empresas_ativo ON empresas(ativo)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_empresas_cnpj ON empresas(cnpj) WHERE cnpj IS NOT NULL")
        
        # Índices de usuarios
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_empresa ON usuarios(empresa_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_ativo ON usuarios(empresa_id, ativo)")
        
        # Índices de veiculos
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_veiculos_empresa ON veiculos(empresa_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_veiculos_placa ON veiculos(placa)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_veiculos_status ON veiculos(empresa_id, status)")
        
        # Índices de fornecedores
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fornecedores_empresa ON fornecedores(empresa_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fornecedores_ativo ON fornecedores(empresa_id, ativo)")
        
        # Índices de pecas
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pecas_empresa ON pecas(empresa_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pecas_codigo ON pecas(codigo)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pecas_fornecedor ON pecas(fornecedor_id) WHERE fornecedor_id IS NOT NULL")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pecas_estoque_baixo ON pecas(empresa_id) WHERE quantidade_estoque <= estoque_minimo")
        
        # Índices de manutencoes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_manutencoes_empresa ON manutencoes(empresa_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_manutencoes_veiculo ON manutencoes(veiculo_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_manutencoes_data ON manutencoes(data_agendada)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_manutencoes_status ON manutencoes(empresa_id, status)")
        
        # Índices de manutencao_pecas
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_manutencao_pecas_manutencao ON manutencao_pecas(manutencao_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_manutencao_pecas_peca ON manutencao_pecas(peca_id)")
        
        # Índices de historico_estoque
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_historico_peca ON historico_estoque(peca_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_historico_data ON historico_estoque(data_operacao)")
        
        # Índices de tecnicos
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tecnicos_empresa ON tecnicos(empresa_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tecnicos_status ON tecnicos(empresa_id, status)")
        
        # Índices de logs
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_usuario ON logs_acoes(usuario_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs_acoes(timestamp)")
        
        # =============================================
        # TRIGGERS PARA UPDATED_AT
        # =============================================
        print("   📝 Criando triggers para updated_at...")
        
        # Função genérica para updated_at
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        """)
        
        # Triggers para cada tabela com updated_at
        tables_with_updated_at = [
            'empresas', 'veiculos', 'fornecedores', 'pecas', 
            'manutencoes', 'tecnicos'
        ]
        
        for table in tables_with_updated_at:
            cursor.execute(f"""
                DROP TRIGGER IF EXISTS trigger_{table}_updated_at ON {table};
                CREATE TRIGGER trigger_{table}_updated_at
                    BEFORE UPDATE ON {table}
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column()
            """)
        
        print("   ✅ Schema PostgreSQL completo!")
    
    def _create_sqlite_schema(self, cursor):
        """Criar schema para SQLite (desenvolvimento local)"""
        
        print("   📝 Criando schema SQLite...")
        
        # Empresas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                nome_fantasia TEXT,
                cnpj TEXT UNIQUE,
                telefone TEXT,
                email TEXT,
                endereco TEXT,
                cidade TEXT,
                estado TEXT,
                cep TEXT,
                plano TEXT DEFAULT 'basico',
                limite_veiculos INTEGER DEFAULT 10,
                limite_usuarios INTEGER DEFAULT 3,
                ativo BOOLEAN DEFAULT 1,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Usuarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                nome TEXT,
                telefone TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'usuario',
                empresa_id INTEGER,
                ativo BOOLEAN DEFAULT 1,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultimo_login TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id)
            )
        """)
        
        # Logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs_acoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                acao TEXT,
                detalhes TEXT,
                ip_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
        """)
        
        # Veiculos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS veiculos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                marca TEXT NOT NULL,
                modelo TEXT NOT NULL,
                placa TEXT NOT NULL,
                ano INTEGER,
                quilometragem INTEGER DEFAULT 0,
                proxima_manutencao DATE,
                status TEXT DEFAULT 'Operacional',
                observacoes TEXT,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                UNIQUE(empresa_id, placa)
            )
        """)
        
        # Fornecedores
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fornecedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                contato TEXT,
                telefone TEXT,
                email TEXT,
                endereco TEXT,
                cnpj TEXT,
                especialidade TEXT,
                ativo BOOLEAN DEFAULT 1,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id)
            )
        """)
        
        # Pecas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pecas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                codigo TEXT NOT NULL,
                descricao TEXT,
                veiculo_compativel TEXT DEFAULT 'Universal',
                preco REAL NOT NULL DEFAULT 0,
                fornecedor_id INTEGER,
                quantidade_estoque INTEGER DEFAULT 0,
                estoque_minimo INTEGER DEFAULT 5,
                unidade TEXT DEFAULT 'UN',
                ativo BOOLEAN DEFAULT 1,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id),
                UNIQUE(empresa_id, codigo)
            )
        """)
        
        # Manutencoes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manutencoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                veiculo_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                descricao TEXT,
                data_agendada DATE NOT NULL,
                data_realizada DATE,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                custo_mao_obra REAL DEFAULT 0,
                custo_total REAL DEFAULT 0,
                status TEXT DEFAULT 'Agendada',
                tecnico TEXT,
                observacoes TEXT,
                km_veiculo INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (veiculo_id) REFERENCES veiculos(id)
            )
        """)
        
        # Manutencao_pecas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manutencao_pecas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manutencao_id INTEGER NOT NULL,
                peca_id INTEGER NOT NULL,
                quantidade INTEGER NOT NULL DEFAULT 1,
                preco_unitario REAL NOT NULL DEFAULT 0,
                subtotal REAL GENERATED ALWAYS AS (quantidade * preco_unitario) STORED,
                data_adicao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                observacoes TEXT,
                FOREIGN KEY (manutencao_id) REFERENCES manutencoes(id),
                FOREIGN KEY (peca_id) REFERENCES pecas(id)
            )
        """)
        
        # Historico_estoque
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_estoque (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                peca_id INTEGER NOT NULL,
                operacao TEXT NOT NULL CHECK(operacao IN ('ENTRADA', 'SAIDA', 'AJUSTE')),
                quantidade_anterior INTEGER NOT NULL,
                quantidade_movimento INTEGER NOT NULL,
                quantidade_nova INTEGER NOT NULL,
                motivo TEXT,
                usuario TEXT DEFAULT 'Sistema',
                data_operacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                manutencao_id INTEGER,
                FOREIGN KEY (peca_id) REFERENCES pecas(id),
                FOREIGN KEY (manutencao_id) REFERENCES manutencoes(id)
            )
        """)
        
        # Tecnicos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tecnicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                cpf TEXT,
                telefone TEXT,
                email TEXT,
                especialidade TEXT,
                data_admissao DATE,
                status TEXT DEFAULT 'Ativo',
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id)
            )
        """)
        
        # Índices básicos para SQLite
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_veiculos_empresa ON veiculos(empresa_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_veiculos_placa ON veiculos(placa)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_manutencoes_veiculo ON manutencoes(veiculo_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pecas_codigo ON pecas(codigo)")
        
        print("   ✅ Schema SQLite completo!")
    
    def down(self):
        """Reverter migração - remover todas as tabelas"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            print("   ⚠️  Removendo todas as tabelas...")
            
            # Ordem inversa de criação (respeitar FKs)
            tables = [
                'historico_estoque',
                'manutencao_pecas', 
                'manutencoes',
                'pecas',
                'fornecedores',
                'veiculos',
                'tecnicos',
                'logs_acoes',
                'usuarios',
                'empresas'
            ]
            
            for table in tables:
                if self.is_postgres:
                    cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                else:
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
            
            # Remover função de trigger (PostgreSQL)
            if self.is_postgres:
                cursor.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
            
            conn.commit()
            print("   ✅ Todas as tabelas removidas!")
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Erro ao reverter schema: {e}")
        finally:
            cursor.close()
            conn.close()
