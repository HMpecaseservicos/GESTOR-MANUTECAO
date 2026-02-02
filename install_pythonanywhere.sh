#!/bin/bash

# =================================================
# Script de Instalação para PythonAnywhere
# =================================================
# Execute este script no Console Bash do PythonAnywhere
# =================================================

echo "🚀 Instalando Gestor de Manutenção de Frota..."
echo ""

# Criar diretório do projeto
echo "📁 Criando diretório do projeto..."
mkdir -p ~/gestor_frota
cd ~/gestor_frota

# Instalar dependências
echo "📦 Instalando dependências Python..."
pip3.11 install --user Flask==3.1.2
pip3.11 install --user Flask-Login==0.6.3
pip3.11 install --user Flask-WTF==1.2.1
pip3.11 install --user Flask-Bcrypt==1.0.1
pip3.11 install --user Flask-Limiter==3.5.0
pip3.11 install --user reportlab==4.4.4
pip3.11 install --user pillow==11.3.0
pip3.11 install --user python-dotenv==1.0.0

echo ""
echo "✅ Instalação concluída!"
echo ""
echo "📋 Próximos passos:"
echo "1. Faça upload dos arquivos do projeto para ~/gestor_frota"
echo "2. Configure o Web App no dashboard"
echo "3. Copie o conteúdo de pythonanywhere_wsgi.py para o arquivo WSGI"
echo "4. Recarregue o Web App"
echo ""
echo "📚 Veja o arquivo DEPLOY_PYTHONANYWHERE_PASSO_A_PASSO.md para instruções completas"
