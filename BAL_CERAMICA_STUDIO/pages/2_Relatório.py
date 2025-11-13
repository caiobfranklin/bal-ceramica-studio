# --- pages/2_Relatório.py (Fase 12.9) ---
# Página dedicada a filtros e geração de PDF.

import streamlit as st
import io

# Importa as funções necessárias do utils.py
from utils import (
    gerar_relatorio_pdf,
    get_public_url
)

# --- V12.1: CSS para esconder o link "app" ---
HIDE_APP_LINK_CSS = """
    <style>
        [data-testid="stSidebarNav"] ul li:first-child {
            display: none;
        }
    </style>
"""
st.markdown(HIDE_APP_LINK_CSS, unsafe_allow_html=True)


# --- Verificação de Segurança ---
if not st.session_state.get('atelie_selecionado_id'):
    st.error("Por favor, selecione um ateliê primeiro na página principal (app.py).")
    st.stop()

# --- Interface da Página ---
st.header("Relatório de Produção")

inventario = st.session_state.inventario # Lê o inventário carregado pelo app.py

if not inventario:
    st.warning("Nenhuma peça foi adicionada ao seu inventário ainda.")
else:
    st.subheader("Filtros do Relatório")
    lista_pessoas = sorted(list(set([p.nome_pessoa for p in inventario if p.nome_pessoa])))
    col1, col2 = st.columns(2)
    filtro_pessoa = col1.multiselect("Filtrar por Pessoa:", options=lista_pessoas)
    filtro_data = col2.text_input("Filtrar por Data de Produção (DD/MM/AAAA):")
    
    lista_para_relatorio = inventario
    if filtro_pessoa:
        lista_para_relatorio = [p for p in lista_para_relatorio if p.nome_pessoa in filtro_pessoa]
    if filtro_data:
        lista_para_relatorio = [p for p in lista_para_relatorio if p.data_producao == filtro_data]
    
    st.subheader("Exportar Relatório")
    nome_do_pdf = gerar_relatorio_pdf(lista_para_relatorio)
    if nome_do_pdf:
        try:
            with open(nome_do_pdf, "rb") as f:
                st.download_button(label="Baixar Relatório em PDF", data=f, file_name=nome_do_pdf, mime="application/pdf")
        except FileNotFoundError: st.error("Erro ao ler o ficheiro PDF gerado.")
    st.divider()
    
    st.subheader(f"Exibindo {len(lista_para_relatorio)} Peças (no filtro)")
    custo_geral_total = 0.0
    totais_por_pessoa = {}
    
    for peca in lista_para_relatorio:
        nome, total_peca = peca.nome_pessoa, peca.total
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Peça:** {peca.tipo_peca} | **Pessoa:** {nome} | **Data:** {peca.data_producao}")
                custo_biscoito_str = f"R$ {peca.custo_biscoito:.2f}".replace('.', ',')
                custo_esmalte_str = f"R$ {peca.custo_esmalte:.2f}".replace('.', ',')
                custo_argila_str = f"R$ {peca.custo_argila:.2f}".replace('.', ',')
                st.write(f"Custos: **Queima de biscoito** ({custo_biscoito_str}), **Queima de esmalte** ({custo_esmalte_str}), **Argila** ({custo_argila_str})")
                
                total_peca_str = f"R$ {peca.total:.2f}".replace('.', ',')
                st.subheader(f"Total da Peça: {total_peca_str}")
            with col2:
                image_url = get_public_url(peca)
                if image_url: st.image(image_url, width=150)
                else: st.caption("Sem foto")
        
        custo_geral_total += total_peca
        total_anterior_pessoa = totais_por_pessoa.get(nome, 0.0) 
        totais_por_pessoa[nome] = total_anterior_pessoa + total_peca
    
    st.divider()
    st.subheader("Resumo Total (do Filtro)")
    col1, col2 = st.columns(2)
    col1.metric(label="Total de Peças na Seleção", value=len(lista_para_relatorio))
    custo_geral_str = f"R$ {custo_geral_total:.2f}".replace('.', ',')
    col2.metric(label="Custo Geral desta Seleção", value=f"{custo_geral_str}")
    
    st.subheader("Resumo por Pessoa (na Seleção)")
    try:
        totais_formatados = {
            "Pessoa": totais_por_pessoa.keys(),
            "Valor Total": [f"RS {v:.2f}".replace('.', ',') for v in totais_por_pessoa.values()]
        }
        st.dataframe(totais_formatados, use_container_width=True)
    except Exception:
        st.dataframe(totais_por_pessoa, use_container_width=True)