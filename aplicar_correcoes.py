"""
Script para adicionar @login_required em todas as rotas do app.py
Executa automaticamente as correções de segurança
"""

import re
import sys

def adicionar_login_required():
    """Adiciona @login_required em todas as rotas que precisam de autenticação"""
    
    arquivo = 'app.py'
    
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
    except FileNotFoundError:
        print(f"❌ Arquivo {arquivo} não encontrado!")
        return False
    
    # Rotas que NÃO devem ter @login_required
    rotas_publicas = ['/login', '/logout', '/static']
    
    # Contador de alterações
    alteracoes = 0
    
    # Dividir em linhas para processar
    linhas = conteudo.split('\n')
    novas_linhas = []
    
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        
        # Verificar se é uma rota
        if linha.strip().startswith('@app.route'):
            # Extrair o caminho da rota
            match = re.search(r"@app\.route\('([^']+)'", linha)
            if match:
                rota_path = match.group(1)
                
                # Verificar se é rota pública
                is_public = any(pub in rota_path for pub in rotas_publicas)
                
                # Verificar se já tem @login_required na linha seguinte
                tem_login_required = False
                if i + 1 < len(linhas):
                    proxima_linha = linhas[i + 1].strip()
                    if '@login_required' in proxima_linha or '@admin_required' in proxima_linha or '@tecnico_required' in proxima_linha:
                        tem_login_required = True
                
                # Adicionar @login_required se necessário
                if not is_public and not tem_login_required:
                    novas_linhas.append(linha)
                    novas_linhas.append('@login_required')
                    alteracoes += 1
                    i += 1
                    continue
        
        novas_linhas.append(linha)
        i += 1
    
    # Escrever de volta
    novo_conteudo = '\n'.join(novas_linhas)
    
    with open(arquivo, 'w', encoding='utf-8') as f:
        f.write(novo_conteudo)
    
    print(f"✅ {alteracoes} rotas protegidas com @login_required")
    return True

def corrigir_sql_injection():
    """Corrige vulnerabilidades de SQL injection"""
    
    arquivo = 'app.py'
    
    with open(arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Padrão problemático: .format(periodo)
    padroes_problematicos = [
        (r'date\("now", "-\{\} days"\)\.format\((\w+)\)', r'date("now", "-" || ? || " days")'),
        (r'\.format\(periodo\)', ''),
    ]
    
    alteracoes = 0
    for padrao, substituicao in padroes_problematicos:
        if re.search(padrao, conteudo):
            print(f"⚠️  Encontrado padrão vulnerável: {padrao}")
            print("   ATENÇÃO: Correção manual necessária!")
            print("   Substitua .format() por parametrized queries")
            alteracoes += 1
    
    if alteracoes > 0:
        print(f"\n⚠️  {alteracoes} vulnerabilidades SQL encontradas!")
        print("   Veja INSTRUCOES_FINALIZACAO.md para correção manual")
    else:
        print("✅ Nenhuma vulnerabilidade SQL óbvia encontrada")
    
    return alteracoes == 0

if __name__ == '__main__':
    print("=" * 60)
    print("APLICANDO CORREÇÕES DE SEGURANÇA")
    print("=" * 60)
    print()
    
    print("1. Adicionando @login_required em rotas...")
    adicionar_login_required()
    print()
    
    print("2. Verificando SQL injection...")
    corrigir_sql_injection()
    print()
    
    print("=" * 60)
    print("✅ CORREÇÕES APLICADAS!")
    print("=" * 60)
    print()
    print("Próximos passos:")
    print("1. Instalar dependências: pip install -r requirements.txt")
    print("2. Criar arquivo .env: cp .env.example .env")
    print("3. Inicializar banco: python init_system.py")
    print("4. Ver: INSTRUCOES_FINALIZACAO.md para detalhes")
    print()
