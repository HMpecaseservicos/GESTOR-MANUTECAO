"""
Script para inicializar o sistema de gestão de frota
Cria o banco de dados e usuário administrador padrão
"""

import os
import sys

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(__file__))

def init_system():
    """Inicializa o sistema completo"""
    
    print("=" * 70)
    print("INICIALIZANDO SISTEMA DE GESTÃO DE MANUTENÇÃO DE FROTA")
    print("=" * 70)
    print()
    
    # Importar após adicionar ao path
    try:
        from app import app, init_db
        from config import Config
    except ImportError as e:
        print(f"❌ Erro ao importar módulos: {e}")
        print()
        print("Certifique-se de que todas as dependências estão instaladas:")
        print("  pip install -r requirements.txt")
        return False
    
    # Garantir diretórios
    print("📁 Criando diretórios necessários...")
    Config.ensure_directories()
    
    # Criar diretório de backups
    os.makedirs('backups', exist_ok=True)
    print("   ✅ Diretórios criados")
    print()
    
    # Verificar arquivo .env
    if not os.path.exists('.env'):
        print("⚠️  Arquivo .env não encontrado!")
        print("   Criando .env a partir de .env.example...")
        try:
            with open('.env.example', 'r') as src, open('.env', 'w') as dst:
                dst.write(src.read())
            print("   ✅ Arquivo .env criado")
            print("   ⚠️  EDITE O ARQUIVO .env E CONFIGURE A SECRET_KEY!")
        except Exception as e:
            print(f"   ❌ Erro ao criar .env: {e}")
            return False
    print()
    
    # Inicializar banco de dados
    print("💾 Inicializando banco de dados...")
    with app.app_context():
        try:
            success = init_db()
            if success:
                print("   ✅ Banco de dados inicializado com sucesso!")
            else:
                print("   ❌ Erro ao inicializar banco de dados")
                return False
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            return False
    print()
    
    # Mostrar credenciais
    print("=" * 70)
    print("✅ SISTEMA INICIALIZADO COM SUCESSO!")
    print("=" * 70)
    print()
    print("🔐 CREDENCIAIS PADRÃO DO ADMINISTRADOR:")
    print("   Usuário: admin")
    print("   Senha: admin123")
    print()
    print("⚠️  IMPORTANTE:")
    print("   1. ALTERE A SENHA DO ADMINISTRADOR IMEDIATAMENTE!")
    print("   2. Configure a SECRET_KEY no arquivo .env")
    print("   3. Revise as configurações de segurança")
    print()
    print("=" * 70)
    print()
    print("🚀 Para iniciar o sistema execute:")
    print("   python app.py")
    print()
    print("   Ou em produção:")
    print("   gunicorn app:app --bind 0.0.0.0:5000 --workers 4")
    print()
    
    return True

if __name__ == '__main__':
    success = init_system()
    sys.exit(0 if success else 1)
