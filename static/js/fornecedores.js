/**
 * Módulo de Fornecedores - GESTOR-MANUTENCAO
 * Gerencia CRUD de fornecedores com busca e filtro client-side
 */

(function() {
    'use strict';

    // Estado global do módulo
    let fornecedorAtual = {};

    // ==========================================
    // INICIALIZAÇÃO
    // ==========================================
    
    document.addEventListener('DOMContentLoaded', function() {
        inicializarEventos();
        inicializarBuscaFiltro();
    });

    function inicializarEventos() {
        // Bloquear submit do form de criação
        const formNovo = document.getElementById('novoFornecedorForm');
        if (formNovo) {
            formNovo.addEventListener('submit', function(e) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            });
        }

        // Botão salvar novo fornecedor
        const btnSalvar = document.getElementById('btnSalvarFornecedor');
        if (btnSalvar) {
            btnSalvar.addEventListener('click', function(e) {
                e.preventDefault();
                salvarFornecedor();
            });
        }

        // Focar no campo nome quando modal abrir
        const modalNovo = document.getElementById('novoFornecedorModal');
        if (modalNovo) {
            modalNovo.addEventListener('shown.bs.modal', function() {
                const inputNome = document.getElementById('inputNomeFornecedor');
                if (inputNome) {
                    setTimeout(() => inputNome.focus(), 150);
                }
            });

            modalNovo.addEventListener('hidden.bs.modal', function() {
                const form = document.getElementById('novoFornecedorForm');
                if (form) form.reset();
            });
        }

        // Event delegation para botões nos cards
        document.addEventListener('click', function(event) {
            const btn = event.target.closest('button');
            if (!btn) return;

            if (btn.classList.contains('btn-detalhes')) {
                const id = btn.getAttribute('data-id');
                if (id) verDetalhesFornecedor(id);
            } else if (btn.classList.contains('btn-editar')) {
                const id = btn.getAttribute('data-id');
                if (id) editarFornecedor(id);
            } else if (btn.classList.contains('btn-excluir')) {
                const id = btn.getAttribute('data-id');
                const nome = btn.getAttribute('data-nome');
                if (id) excluirFornecedor(id, nome);
            } else if (btn.classList.contains('btn-whatsapp')) {
                const telefone = btn.getAttribute('data-telefone');
                const nome = btn.getAttribute('data-nome');
                if (telefone) contatarFornecedorWhatsApp(telefone, nome);
            }
        });
    }

    // ==========================================
    // BUSCA E FILTRO
    // ==========================================

    function inicializarBuscaFiltro() {
        const inputBusca = document.getElementById('searchFornecedores');
        const selectEspecialidade = document.getElementById('filterEspecialidade');
        const btnBuscar = document.getElementById('btnBuscar');

        if (inputBusca) {
            inputBusca.addEventListener('input', debounce(aplicarFiltros, 300));
            inputBusca.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    aplicarFiltros();
                }
            });
        }

        if (selectEspecialidade) {
            selectEspecialidade.addEventListener('change', aplicarFiltros);
        }

        if (btnBuscar) {
            btnBuscar.addEventListener('click', function(e) {
                e.preventDefault();
                aplicarFiltros();
            });
        }
    }

    function aplicarFiltros() {
        const termoBusca = (document.getElementById('searchFornecedores')?.value || '').toLowerCase().trim();
        const especialidadeFiltro = (document.getElementById('filterEspecialidade')?.value || '').toLowerCase();
        
        const cards = document.querySelectorAll('.fornecedor-card');
        let visiveis = 0;

        cards.forEach(function(card) {
            const nome = (card.getAttribute('data-nome') || '').toLowerCase();
            const especialidade = (card.getAttribute('data-especialidade') || '').toLowerCase();

            const matchNome = !termoBusca || nome.includes(termoBusca);
            const matchEspecialidade = !especialidadeFiltro || especialidade.includes(especialidadeFiltro);

            if (matchNome && matchEspecialidade) {
                card.style.display = '';
                visiveis++;
            } else {
                card.style.display = 'none';
            }
        });

        // Atualizar contador de resultados
        atualizarContadorResultados(visiveis, cards.length);
    }

    function atualizarContadorResultados(visiveis, total) {
        let contador = document.getElementById('contadorResultados');
        
        if (!contador) {
            const containerBusca = document.querySelector('.row.mb-3');
            if (containerBusca) {
                contador = document.createElement('div');
                contador.id = 'contadorResultados';
                contador.className = 'col-12 mt-2';
                containerBusca.appendChild(contador);
            }
        }

        if (contador) {
            if (visiveis === total) {
                contador.innerHTML = '';
            } else {
                contador.innerHTML = `<small class="text-muted"><i class="fas fa-filter"></i> Exibindo ${visiveis} de ${total} fornecedores</small>`;
            }
        }
    }

    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    // ==========================================
    // CRUD - CRIAR
    // ==========================================

    function salvarFornecedor() {
        const modal = document.getElementById('novoFornecedorModal');
        
        const getValue = (selector) => {
            const el = modal.querySelector(selector);
            return el ? el.value.trim() : '';
        };

        const nome = getValue('input[name="nome"]');
        
        if (!nome) {
            alert('⚠️ O nome da empresa é obrigatório!');
            return;
        }

        const dados = {
            nome: nome,
            contato: getValue('input[name="contato"]'),
            telefone: getValue('input[name="telefone"]'),
            email: getValue('input[name="email"]'),
            especialidade: getValue('select[name="especialidade"]'),
            cnpj: getValue('input[name="cnpj"]'),
            endereco: getValue('input[name="endereco"]')
        };

        fetch('/fornecedores/criar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                alert('✅ Fornecedor cadastrado com sucesso!');
                location.reload();
            } else {
                alert('❌ Erro: ' + (result.message || 'Erro desconhecido'));
            }
        })
        .catch(() => {
            alert('❌ Falha na conexão com o servidor');
        });
    }

    // ==========================================
    // CRUD - DETALHES
    // ==========================================

    function verDetalhesFornecedor(id) {
        fetch(`/fornecedores/detalhes/${id}`)
            .then(response => response.json())
            .then(fornecedor => {
                fornecedorAtual = fornecedor;

                const setText = (elementId, value, fallback = 'Não informado') => {
                    const el = document.getElementById(elementId);
                    if (el) el.textContent = value || fallback;
                };

                setText('detalhe-nome', fornecedor.nome);
                setText('detalhe-contato', fornecedor.contato);
                setText('detalhe-telefone', fornecedor.telefone);
                setText('detalhe-email', fornecedor.email);
                setText('detalhe-especialidade', fornecedor.especialidade);
                setText('detalhe-cnpj', fornecedor.cnpj);
                setText('detalhe-endereco', fornecedor.endereco);

                const modal = new bootstrap.Modal(document.getElementById('detalhesFornecedorModal'));
                modal.show();
            })
            .catch(() => {
                alert('❌ Erro ao carregar detalhes do fornecedor');
            });
    }

    // ==========================================
    // CRUD - EDITAR
    // ==========================================

    function editarFornecedor(id) {
        fetch(`/fornecedores/detalhes/${id}`)
            .then(response => response.json())
            .then(fornecedor => {
                const setValue = (elementId, value) => {
                    const el = document.getElementById(elementId);
                    if (el) el.value = value || '';
                };

                setValue('edit-id', fornecedor.id);
                setValue('edit-nome', fornecedor.nome);
                setValue('edit-contato', fornecedor.contato);
                setValue('edit-telefone', fornecedor.telefone);
                setValue('edit-email', fornecedor.email);
                setValue('edit-especialidade', fornecedor.especialidade);
                setValue('edit-cnpj', fornecedor.cnpj);
                setValue('edit-endereco', fornecedor.endereco);

                const modal = new bootstrap.Modal(document.getElementById('editarFornecedorModal'));
                modal.show();
            })
            .catch(() => {
                alert('❌ Erro ao carregar dados do fornecedor');
            });
    }

    function salvarEdicaoFornecedor() {
        const id = document.getElementById('edit-id')?.value;
        
        if (!id) {
            alert('❌ ID do fornecedor não encontrado');
            return;
        }

        const getValue = (elementId) => {
            const el = document.getElementById(elementId);
            return el ? el.value.trim() : '';
        };

        const nome = getValue('edit-nome');
        if (!nome) {
            alert('⚠️ O nome da empresa é obrigatório!');
            return;
        }

        const dados = {
            nome: nome,
            contato: getValue('edit-contato'),
            telefone: getValue('edit-telefone'),
            email: getValue('edit-email'),
            especialidade: getValue('edit-especialidade'),
            cnpj: getValue('edit-cnpj'),
            endereco: getValue('edit-endereco')
        };

        fetch(`/fornecedores/editar/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('✅ Fornecedor atualizado com sucesso!');
                location.reload();
            } else {
                alert('❌ Erro ao atualizar: ' + (data.error || data.message || 'Erro desconhecido'));
            }
        })
        .catch(() => {
            alert('❌ Erro ao salvar alterações');
        });
    }

    // ==========================================
    // CRUD - EXCLUIR
    // ==========================================

    function excluirFornecedor(id, nome) {
        if (!confirm(`⚠️ Tem certeza que deseja excluir o fornecedor "${nome}"?\n\nEsta ação não pode ser desfeita!`)) {
            return;
        }

        fetch(`/fornecedores/excluir/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('✅ Fornecedor excluído com sucesso!');
                location.reload();
            } else {
                alert('❌ Erro ao excluir: ' + (data.error || 'Erro desconhecido'));
            }
        })
        .catch(() => {
            alert('❌ Erro ao excluir fornecedor');
        });
    }

    // ==========================================
    // WHATSAPP
    // ==========================================

    function contatarFornecedorWhatsApp(telefone, nomeFornecedor) {
        if (!telefone || telefone === 'Não informado') {
            alert('📱 Telefone não cadastrado para este fornecedor');
            return;
        }

        const numeroLimpo = telefone.replace(/\D/g, '');
        const mensagem = encodeURIComponent(
            `Olá ${nomeFornecedor}! Entrando em contato pelo sistema de Gestão de Frota.`
        );

        window.open(`https://wa.me/55${numeroLimpo}?text=${mensagem}`, '_blank');
    }

    function contatarWhatsAppDetalhes() {
        contatarFornecedorWhatsApp(fornecedorAtual.telefone, fornecedorAtual.nome);
    }

    // ==========================================
    // EXPORTAR FUNÇÕES GLOBAIS
    // ==========================================
    
    // Expor funções que são chamadas via onclick no HTML
    window.salvarFornecedor = salvarFornecedor;
    window.salvarEdicaoFornecedor = salvarEdicaoFornecedor;
    window.contatarWhatsAppDetalhes = contatarWhatsAppDetalhes;
    window.verDetalhesFornecedor = verDetalhesFornecedor;
    window.editarFornecedor = editarFornecedor;
    window.excluirFornecedor = excluirFornecedor;
    window.contatarFornecedorWhatsApp = contatarFornecedorWhatsApp;

})();
