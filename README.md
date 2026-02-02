# 🚛 Sistema de Gestão de Manutenção de Frota v2.0 Professional

Sistema profissional completo para gerenciamento de manutenção de veículos e máquinas, com controle automático de peças e interface moderna.

## 🚀 Funcionalidades

### ✅ Dashboard
- Visão geral da frota
- Estatísticas de manutenção
- Alertas e notificações
- Indicadores de performance

### ✅ Gestão de Veículos
- Cadastro completo de veículos
- Histórico de manutenções
- Catálogo de peças compatíveis
- Status operacional

### ✅ Controle de Manutenção
- Agendamento de serviços
- Acompanhamento de status
- Tipos: Preventiva, Corretiva, Emergencial
- Controle de custos

### ✅ Gestão de Peças
- Catálogo de peças
- Controle de estoque
- Alertas de estoque baixo
- Compatibilidade com veículos

### ✅ Fornecedores
- Cadastro de fornecedores
- Contatos e especialidades
- Histórico de compras
- Avaliações

### ✅ Chatbot Integrado
- Consulta de manutenções
- Verificação de estoque
- Contatos de fornecedores
- Suporte técnico 24/7

### ✅ Relatórios
- Custos de manutenção
- Análise de veículos
- Estatísticas mensais
- Exportação em PDF/Excel

## 🛠️ Tecnologias Utilizadas

- **Backend:** Flask (Python)
- **Banco de Dados:** SQLite
- **Frontend:** Bootstrap 5, HTML5, CSS3, JavaScript
- **Gráficos:** Chart.js
- **Ícones:** Font Awesome

## 📋 Pré-requisitos

- Python 3.7+
- pip (gerenciador de pacotes Python)

## 🔧 Instalação

1. **Clone ou baixe os arquivos do projeto**
   ```bash
   cd c:\gestor\GestorManutencaoFrota
   ```

2. **Crie um ambiente virtual (recomendado)**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

4. **Execute a aplicação**
   ```bash
   python app.py
   ```

5. **Acesse no navegador**
   ```
   http://localhost:5000
   ```

## 📂 Estrutura do Projeto

```
GestorManutencaoFrota/
├── app.py                 # Aplicação principal Flask
├── requirements.txt       # Dependências Python
├── README.md             # Este arquivo
├── database/
│   └── frota.db          # Banco de dados SQLite
├── templates/            # Templates HTML
│   ├── base.html         # Template base
│   ├── dashboard.html    # Dashboard principal
│   ├── veiculos.html     # Gestão de veículos
│   ├── detalhes_veiculo.html # Detalhes do veículo
│   ├── manutencao.html   # Gestão de manutenção
│   ├── pecas.html        # Gestão de peças
│   ├── fornecedores.html # Gestão de fornecedores
│   └── relatorios.html   # Relatórios e análises
└── static/               # Arquivos estáticos
    ├── css/
    │   └── style.css     # Estilos personalizados
    └── js/
        └── script.js     # JavaScript personalizado
```

## 🎯 Como Usar

### Dashboard
1. Acesse a página inicial para ver o resumo da frota
2. Verifique alertas de manutenção e estoque
3. Monitore estatísticas em tempo real

### Cadastrar Veículo
1. Vá em "Veículos" → "Novo Veículo"
2. Preencha as informações obrigatórias
3. Defina a data da próxima manutenção

### Agendar Manutenção
1. Acesse "Manutenção" → "Nova Manutenção"
2. Selecione o veículo e tipo de manutenção
3. Defina data e técnico responsável

### Gerenciar Estoque
1. Em "Peças", cadastre novas peças
2. Monitore alertas de estoque baixo
3. Associe peças aos fornecedores

### Usar o Chatbot
1. Clique no ícone de chat no canto inferior direito
2. Digite suas perguntas sobre:
   - Próximas manutenções
   - Estoque de peças
   - Contatos de fornecedores

## 📊 Relatórios Disponíveis

- **Custos por Mês:** Acompanhe gastos mensais
- **Veículos Críticos:** Identifique veículos com mais problemas
- **Performance da Frota:** KPIs e indicadores
- **Estoque:** Relatório de peças e fornecedores

## 🔒 Segurança

- Validação de dados no frontend e backend
- Proteção contra SQL Injection
- Sanitização de inputs do usuário
- Logs de atividade

## 🎨 Personalização

### Cores e Tema
Edite o arquivo `static/css/style.css` para personalizar:
- Cores primárias
- Layout dos cards
- Estilo do chatbot

### Funcionalidades
Modifique `app.py` para:
- Adicionar novas rotas
- Personalizar banco de dados
- Integrar com APIs externas

## 🐛 Solução de Problemas

### Banco de dados não encontrado
```bash
# O banco será criado automaticamente na primeira execução
python app.py
```

### Erro de porta ocupada
```python
# No arquivo app.py, mude a porta:
app.run(debug=True, port=5001)
```

### Problemas com dependências
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

## 📈 Próximas Funcionalidades

- [ ] Integração com GPS para rastreamento
- [ ] Notificações via email/SMS
- [ ] App mobile
- [ ] Integração com sistema de combustível
- [ ] Dashboard executivo
- [ ] Backup automático
- [ ] Multi-usuário com permissões

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 📞 Suporte

Para dúvidas e suporte:
- Consulte este README
- Use o chatbot integrado no sistema
- Verifique os logs da aplicação

## 📊 Estatísticas do Sistema

- **Tempo de desenvolvimento:** 2 dias
- **Linhas de código:** ~2.500
- **Funcionalidades:** 15+
- **Templates:** 7
- **Compatibilidade:** Windows, Linux, macOS

---

**Desenvolvido com ❤️ para otimizar a gestão da sua frota!**