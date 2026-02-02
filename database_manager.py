"""
Sistema de Banco de Dados - Gestor de Manutenção de Frota
=========================================================

Este módulo gerencia todas as operações de banco de dados do sistema,
incluindo inicialização, migrações e operações CRUD.
"""

import sqlite3
import os
from datetime import datetime
from config import Config

class DatabaseManager:
    """Gerenciador principal do banco de dados"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or Config.DATABASE_PATH
        Config.ensure_directories()
    
    def get_connection(self):
        """Obtém uma conexão com o banco de dados"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Permite acesso por nome da coluna
        return conn
    
    def execute_script(self, script):
        """Executa um script SQL"""
        conn = self.get_connection()
        try:
            conn.executescript(script)
            conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao executar script: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def init_database(self):
        """Inicializa o banco de dados com todas as tabelas"""
        
        # Script de criação das tabelas
        init_script = """
        -- =============================================
        -- SCHEMA DO BANCO DE DADOS
        -- Sistema de Gestão de Manutenção de Frota
        -- =============================================
        
        -- Tabela de Veículos
        CREATE TABLE IF NOT EXISTS veiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL CHECK(tipo IN ('Caminhão', 'Máquina', 'Van', 'Utilitário')),
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            placa TEXT UNIQUE NOT NULL,
            ano INTEGER CHECK(ano >= 1980 AND ano <= 2030),
            quilometragem INTEGER DEFAULT 0,
            proxima_manutencao DATE,
            status TEXT DEFAULT 'Operacional' CHECK(status IN ('Operacional', 'Manutenção', 'Inativo')),
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            observacoes TEXT
        );
        
        -- Tabela de Fornecedores
        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            contato TEXT,
            telefone TEXT,
            email TEXT,
            endereco TEXT,
            cnpj TEXT,
            especialidade TEXT,
            ativo BOOLEAN DEFAULT 1,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Tabela de Peças
        CREATE TABLE IF NOT EXISTS pecas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            codigo TEXT UNIQUE NOT NULL,
            descricao TEXT,
            veiculo_compativel TEXT DEFAULT 'Universal',
            preco REAL NOT NULL CHECK(preco >= 0),
            fornecedor_id INTEGER,
            quantidade_estoque INTEGER DEFAULT 0 CHECK(quantidade_estoque >= 0),
            estoque_minimo INTEGER DEFAULT 5,
            unidade TEXT DEFAULT 'UN',
            ativo BOOLEAN DEFAULT 1,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fornecedor_id) REFERENCES fornecedores (id)
        );
        
        -- Tabela de Manutenções
        CREATE TABLE IF NOT EXISTS manutencoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            veiculo_id INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('Preventiva', 'Corretiva', 'Emergencial', 'Revisão')),
            descricao TEXT,
            data_agendada DATE NOT NULL,
            data_realizada DATE,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            custo_mao_obra REAL DEFAULT 0,
            custo_total REAL DEFAULT 0,
            status TEXT DEFAULT 'Agendada' CHECK(status IN ('Agendada', 'Em Andamento', 'Concluída', 'Cancelada')),
            tecnico TEXT,
            observacoes TEXT,
            km_veiculo INTEGER,
            FOREIGN KEY (veiculo_id) REFERENCES veiculos (id)
        );
        
        -- Tabela de Peças utilizadas nas Manutenções
        CREATE TABLE IF NOT EXISTS manutencao_pecas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manutencao_id INTEGER NOT NULL,
            peca_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL CHECK(quantidade > 0),
            preco_unitario REAL NOT NULL CHECK(preco_unitario >= 0),
            subtotal REAL GENERATED ALWAYS AS (quantidade * preco_unitario) STORED,
            data_adicao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            observacoes TEXT,
            FOREIGN KEY (manutencao_id) REFERENCES manutencoes (id) ON DELETE CASCADE,
            FOREIGN KEY (peca_id) REFERENCES pecas (id)
        );
        
        -- Tabela de Histórico de Estoque (para auditoria)
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
            FOREIGN KEY (peca_id) REFERENCES pecas (id),
            FOREIGN KEY (manutencao_id) REFERENCES manutencoes (id)
        );
        
        -- =============================================
        -- ÍNDICES PARA PERFORMANCE
        -- =============================================
        
        CREATE INDEX IF NOT EXISTS idx_veiculos_placa ON veiculos(placa);
        CREATE INDEX IF NOT EXISTS idx_veiculos_status ON veiculos(status);
        CREATE INDEX IF NOT EXISTS idx_manutencoes_veiculo ON manutencoes(veiculo_id);
        CREATE INDEX IF NOT EXISTS idx_manutencoes_data ON manutencoes(data_agendada);
        CREATE INDEX IF NOT EXISTS idx_manutencoes_status ON manutencoes(status);
        CREATE INDEX IF NOT EXISTS idx_pecas_codigo ON pecas(codigo);
        CREATE INDEX IF NOT EXISTS idx_manutencao_pecas_manutencao ON manutencao_pecas(manutencao_id);
        CREATE INDEX IF NOT EXISTS idx_historico_estoque_peca ON historico_estoque(peca_id);
        
        -- =============================================
        -- TRIGGERS PARA INTEGRIDADE E AUDITORIA
        -- =============================================
        
        -- Trigger para atualizar custo total da manutenção
        CREATE TRIGGER IF NOT EXISTS update_custo_total_manutencao
        AFTER INSERT ON manutencao_pecas
        BEGIN
            UPDATE manutencoes 
            SET custo_total = custo_mao_obra + (
                SELECT COALESCE(SUM(subtotal), 0) 
                FROM manutencao_pecas 
                WHERE manutencao_id = NEW.manutencao_id
            )
            WHERE id = NEW.manutencao_id;
        END;
        
        -- Trigger para registrar histórico de estoque ao usar peças
        CREATE TRIGGER IF NOT EXISTS historico_uso_peca
        AFTER INSERT ON manutencao_pecas
        BEGIN
            INSERT INTO historico_estoque (
                peca_id, operacao, quantidade_anterior, quantidade_movimento, 
                quantidade_nova, motivo, manutencao_id
            )
            SELECT 
                NEW.peca_id,
                'SAIDA',
                p.quantidade_estoque + NEW.quantidade,
                NEW.quantidade,
                p.quantidade_estoque,
                'Uso em manutenção ID: ' || NEW.manutencao_id,
                NEW.manutencao_id
            FROM pecas p WHERE p.id = NEW.peca_id;
        END;
        """
        
        if self.execute_script(init_script):
            print("✅ Banco de dados inicializado com sucesso!")
            return True
        else:
            print("❌ Erro ao inicializar banco de dados!")
            return False
    
    def insert_sample_data(self):
        """Insere dados de exemplo para demonstração"""
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Verificar se já existem dados
            cursor.execute("SELECT COUNT(*) FROM veiculos")
            if cursor.fetchone()[0] > 0:
                print("⚠️ Dados de exemplo já existem. Pulando inserção.")
                return True
            
            # Inserir fornecedores
            fornecedores_sample = [
                ('Auto Peças Premium Ltda', 'João Silva', '(11) 99999-8888', 'joao@autopecas.com', 
                 'Rua das Peças, 123', '12.345.678/0001-90', 'Peças para caminhões'),
                ('Mecânica Especializada', 'Maria Santos', '(11) 77777-6666', 'maria@mecanica.com',
                 'Av. Conserto, 456', '98.765.432/0001-10', 'Serviços mecânicos'),
                ('Pneus & Rodas Express', 'Carlos Oliveira', '(11) 55555-4444', 'carlos@pneus.com',
                 'Rua do Pneu, 789', '11.222.333/0001-44', 'Pneus e rodas'),
                ('Filtros & Óleos SA', 'Ana Costa', '(11) 33333-2222', 'ana@filtros.com',
                 'Av. Lubrificação, 321', '44.555.666/0001-77', 'Filtros e lubrificantes')
            ]
            
            cursor.executemany('''
                INSERT INTO fornecedores (nome, contato, telefone, email, endereco, cnpj, especialidade)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', fornecedores_sample)
            
            # Inserir veículos
            veiculos_sample = [
                ('Caminhão', 'Volvo', 'FH 540', 'ABC-1D23', 2020, 150000, '2024-02-15', 'Operacional'),
                ('Caminhão', 'Mercedes-Benz', 'Actros 2646', 'DEF-4G56', 2019, 180000, '2024-01-30', 'Operacional'),
                ('Máquina', 'Caterpillar', '320D Escavadeira', 'GHI-7J89', 2021, 2500, '2024-03-10', 'Operacional'),
                ('Caminhão', 'Scania', 'R450 A6x4', 'KLM-0N12', 2022, 80000, '2024-04-05', 'Operacional'),
                ('Van', 'Ford', 'Transit', 'MNO-3P45', 2023, 25000, '2024-05-15', 'Operacional')
            ]
            
            cursor.executemany('''
                INSERT INTO veiculos (tipo, marca, modelo, placa, ano, quilometragem, proxima_manutencao, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', veiculos_sample)
            
            # Inserir peças com estoque
            pecas_sample = [
                ('Filtro de Óleo Motor', 'FO-VOL-001', 'Filtro original Volvo', 'Volvo', 45.90, 1, 25, 5, 'UN'),
                ('Pastilha de Freio Dianteira', 'PF-MB-002', 'Pastilha cerâmica Mercedes', 'Mercedes-Benz', 120.50, 1, 18, 4, 'JG'),
                ('Kit Correia Dentada', 'KC-CAT-003', 'Kit completo Caterpillar', 'Caterpillar', 289.90, 2, 10, 2, 'KT'),
                ('Filtro de Combustível', 'FC-SCA-004', 'Filtro diesel Scania', 'Scania', 65.30, 1, 20, 5, 'UN'),
                ('Amortecedor Dianteiro', 'AD-VOL-005', 'Amortecedor a gás Volvo', 'Volvo', 285.00, 1, 8, 2, 'UN'),
                ('Disco de Freio', 'DF-MB-006', 'Disco ventilado Mercedes', 'Mercedes-Benz', 189.50, 1, 12, 3, 'PC'),
                ('Vela de Ignição', 'VI-FORD-007', 'Vela iridium Ford', 'Ford', 24.90, 2, 30, 10, 'UN'),
                ('Filtro de Ar', 'FA-UNI-008', 'Filtro de ar universal', 'Universal', 38.75, 4, 35, 8, 'UN'),
                ('Óleo Motor 15W40', 'OM-UNI-009', 'Óleo mineral 20L', 'Universal', 178.90, 4, 15, 3, 'BD'),
                ('Pneu 295/80R22.5', 'PN-UNI-010', 'Pneu radial para caminhão', 'Universal', 890.00, 3, 16, 4, 'UN'),
                ('Bateria 150Ah', 'BT-UNI-011', 'Bateria estacionária', 'Universal', 420.00, 2, 6, 2, 'UN'),
                ('Kit Lâmpadas H7', 'LH-UNI-012', 'Kit lâmpadas LED', 'Universal', 85.50, 2, 25, 10, 'KT')
            ]
            
            cursor.executemany('''
                INSERT INTO pecas (nome, codigo, descricao, veiculo_compativel, preco, fornecedor_id, 
                                 quantidade_estoque, estoque_minimo, unidade)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', pecas_sample)
            
            # Inserir algumas manutenções de exemplo
            manutencoes_sample = [
                (1, 'Preventiva', 'Troca de óleo, filtros e revisão geral', '2024-02-15', None, 250.00, 'Agendada', 'João Silva', None, 150000),
                (2, 'Corretiva', 'Reparo no sistema de freios - pastilhas gastas', '2024-01-30', None, 180.00, 'Agendada', 'Maria Santos', None, 180000),
                (3, 'Preventiva', 'Revisão de 2500 horas - máquina escavadeira', '2024-03-10', None, 400.00, 'Agendada', 'Carlos Oliveira', None, 2500),
                (4, 'Emergencial', 'Vazamento de óleo no motor', '2024-01-25', '2024-01-25', 320.00, 'Concluída', 'João Silva', 'Reparo emergencial executado', 80000)
            ]
            
            cursor.executemany('''
                INSERT INTO manutencoes (veiculo_id, tipo, descricao, data_agendada, data_realizada, 
                                       custo_mao_obra, status, tecnico, observacoes, km_veiculo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', manutencoes_sample)
            
            conn.commit()
            print("✅ Dados de exemplo inseridos com sucesso!")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao inserir dados de exemplo: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def backup_database(self, backup_path=None):
        """Cria backup do banco de dados"""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_frota_{timestamp}.db"
        
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            print(f"✅ Backup criado: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Erro ao criar backup: {e}")
            return False

# Instância global do gerenciador
db_manager = DatabaseManager()

def init_db():
    """Função de conveniência para inicialização"""
    success = db_manager.init_database()
    if success:
        db_manager.insert_sample_data()
    return success

def get_db():
    """Função de conveniência para obter conexão"""
    return db_manager.get_connection()