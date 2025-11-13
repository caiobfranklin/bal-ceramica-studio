# --- pages/1_Inventário.py ---
# Esta é a página principal para gerir as peças.

import streamlit as st
import io

# Importa TODAS as nossas funções e objetos do utils.py
from utils import (
    supabase, 
    Peca,
    # st, # <- REMOVIDO DAQUI
    get_public_url,
    salvar_nova_peca,
    atualizar_peca_db,
    excluir_peca_db,
    set_estado_inventario_lista,
    set_estado_inventario_adicionar,
    set_estado_inventario_editar
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


# --- V12.0: Verificação de Segurança ---
if not st.session_state.get('atelie_selecionado_id'):
    st.error("Por favor, selecione um ateliê primeiro na página principal (app.py).")
    st.stop()

# --- Roteador da Página de Inventário ---
# (O resto deste ficheiro é idêntico ao v11.0 que enviei antes)
estado_atual = st.session_state.pagina_inventario_estado

# --- ESTADO 1: MOSTRAR FORMULÁRIO DE ADICIONAR ---
if estado_atual == 'adicionar':
    st.header("Adicionar Nova Peça")
    
    with st.form(key="nova_peca_form"):
        st.subheader("Dados da Peça")
        nome_pessoa = st.text_input("Quem produziu a peça?")
        tipo_peca = st.text_input("Qual o tipo de peça? (Ex: Copo, Vaso)")
        data_producao = st.text_input("Qual a data de produção? (DD/MM/AAAA)")
        uploaded_file = st.file_uploader("Anexar foto da peça", type=["png", "jpg", "jpeg"])
        st.subheader("Medidas")
        peso_kg = st.number_input("Peso (kg)?", min_value=0.0, format="%.3f")
        altura_cm = st.number_input("Altura (cm)?", min_value=0.0, format="%.2f")
        largura_cm = st.number_input("Largura (cm)?", min_value=0.0, format="%.2f")
        profundidade_cm = st.number_input("Profundidade (cm)?", min_value=0.0, format="%.2f")
        st.subheader("Custos de Material")
        
        preco_argila_atual = st.session_state.precos_atelie['argila_kg']
        texto_argila_atelie = f"Argila do Ateliê (R$ {preco_argila_atual:.2f}".replace('.',',') + "/kg)"
        
        tipo_argila_escolha = st.radio("Qual argila foi usada?",
                                    ("Argila Própria", texto_argila_atelie), 
                                    index=0)
        preco_argila_propria_input = 0.0
        if tipo_argila_escolha == "Argila Própria":
            tipo_argila_final = 'propria'
            preco_argila_propria_input = st.number_input("Preço do kg da sua argila? (R$)", min_value=0.0, format="%.2f")
        else:
            tipo_argila_final = 'atelie'
        
        col_salvar, col_cancelar = st.columns(2)
        submit_button = col_salvar.form_submit_button(label="Adicionar e Salvar Peça", use_container_width=True)
        # O botão Cancelar usa o callback para mudar o estado
        if col_cancelar.form_submit_button(label="Cancelar", type="secondary", use_container_width=True, on_click=set_estado_inventario_lista):
            pass # O callback on_click fará o trabalho

    if submit_button:
        if not nome_pessoa or not tipo_peca or not data_producao or peso_kg == 0:
            st.error("Por favor, preencha pelo menos o Nome, Tipo, Data e Peso (peso não pode ser zero).")
        else:
            with st.spinner("A criar e salvar a nova peça..."):
                nova_peca = Peca(
                    data_producao=data_producao, nome_pessoa=nome_pessoa, tipo_peca=tipo_peca,
                    peso_kg=peso_kg, altura_cm=altura_cm, largura_cm=largura_cm,
                    profundidade_cm=profundidade_cm, 
                    tipo_argila=tipo_argila_final, preco_argila_propria=preco_argila_propria_input
                )
                nova_peca.recalcular_custos(st.session_state.precos_atelie)
                
                if salvar_nova_peca(nova_peca, uploaded_file):
                    st.success(f"✅ Peça '{nova_peca.tipo_peca}' adicionada!")
                    st.balloons()
                    st.session_state.inventario.insert(0, nova_peca) 
                    set_estado_inventario_lista() # Volta para a lista
                    st.rerun()
                else: 
                    st.error("Erro ao salvar os dados no Supabase.")

# --- ESTADO 2: MOSTRAR FORMULÁRIO DE EDITAR ---
elif estado_atual != 'lista': # O estado é um ID de peça
    st.header("Editar Peça")
    
    # Encontra a peça a ser editada
    peca_obj_original = next((p for p in st.session_state.inventario if p.id == estado_atual), None)

    if peca_obj_original:
        with st.form(key="editar_peca_form"):
            st.subheader(f"A editar: {peca_obj_original.tipo_peca} (por {peca_obj_original.nome_pessoa})")
            st.subheader("Dados da Peça")
            nome_pessoa = st.text_input("Quem produziu", value=peca_obj_original.nome_pessoa)
            tipo_peca = st.text_input("Tipo de peça", value=peca_obj_original.tipo_peca)
            data_producao = st.text_input("Data de produção", value=peca_obj_original.data_producao)
            
            st.subheader("Medidas")
            peso_kg = st.number_input("Peso (kg)", value=peca_obj_original.peso_kg, format="%.3f")
            altura_cm = st.number_input("Altura (cm)", value=peca_obj_original.altura_cm, format="%.2f")
            largura_cm = st.number_input("Largura (cm)", value=peca_obj_original.largura_cm, format="%.2f")
            profundidade_cm = st.number_input("Profundidade (cm)", value=peca_obj_original.profundidade_cm, format="%.2f")
            
            st.subheader("Custos de Material")
            preco_argila_atual = st.session_state.precos_atelie['argila_kg']
            texto_argila_atelie = f"Argila do Ateliê (R$ {preco_argila_atual:.2f}".replace('.',',') + "/kg)"
            index_argila = 1 if peca_obj_original.tipo_argila == 'atelie' else 0
            
            tipo_argila_escolha = st.radio("Qual argila foi usada?",
                                        ("Argila Própria", texto_argila_atelie), 
                                        index=index_argila)
            
            preco_argila_propria_input = st.number_input("Preço do kg da sua argila? (R$)", 
                                                         value=peca_obj_original.preco_argila_propria, format="%.2f")

            st.subheader("Foto")
            if peca_obj_original.image_path:
                st.caption("Foto atual:")
                st.image(get_public_url(peca_obj_original), width=200)
            uploaded_file = st.file_uploader("Trocar foto (opcional)", type=["png", "jpg", "jpeg"])
            
            col_salvar, col_cancelar = st.columns(2)
            submit_button = col_salvar.form_submit_button("Salvar Alterações", use_container_width=True)
            if col_cancelar.form_submit_button("Cancelar", type="secondary", use_container_width=True, on_click=set_estado_inventario_lista):
                pass # Callback faz o trabalho

        if submit_button:
            # Atualiza o objeto com os novos valores
            peca_obj_original.nome_pessoa = nome_pessoa
            peca_obj_original.tipo_peca = tipo_peca
            peca_obj_original.data_producao = data_producao
            peca_obj_original.peso_kg = peso_kg
            peca_obj_original.altura_cm = altura_cm
            peca_obj_original.largura_cm = largura_cm
            peca_obj_original.profundidade_cm = profundidade_cm
            peca_obj_original.tipo_argila = 'atelie' if tipo_argila_escolha == texto_argila_atelie else 'propria'
            peca_obj_original.preco_argila_propria = preco_argila_propria_input
            
            with st.spinner("A atualizar a peça..."):
                if atualizar_peca_db(peca_obj_original, uploaded_file):
                    st.success("Peça atualizada com sucesso!")
                    set_estado_inventario_lista() # Volta para a lista
                    st.rerun() 
                else:
                    st.error("Falha ao atualizar a peça.")
    else:
        st.error("Erro: Peça não encontrada. A voltar para a lista.")
        set_estado_inventario_lista()
        st.rerun()

# --- ESTADO 3: MOSTRAR LISTA DE INVENTÁRIO (PADRÃO) ---
else: # estado_atual == 'lista'
    st.header("Inventário do Ateliê")
    
    # Botão Adicionar usa o callback para mudar o estado
    st.button("＋ Adicionar Nova Peça", type="primary", use_container_width=True, on_click=set_estado_inventario_adicionar)
    
    st.divider()

    inventario = st.session_state.inventario
    if not inventario:
        st.info("Nenhuma peça foi adicionada a este ateliê ainda.")
    else:
        st.subheader(f"Exibindo {len(inventario)} Peças")
        
        for peca in inventario:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**Peça:** {peca.tipo_peca} | **Pessoa:** {peca.nome_pessoa} | **Data:** {peca.data_producao}")
                    total_peca_str = f"R$ {peca.total:.2f}".replace('.', ',')
                    st.subheader(f"Custo Total: {total_peca_str}")
                    
                    # Botões de Ação
                    col_b1, col_b2 = st.columns(2)
                    col_b1.button("Editar ✏️", key=f"edit_{peca.id}", 
                                  on_click=set_estado_inventario_editar, 
                                  args=(peca.id,), use_container_width=True)
                    
                    # Botão de excluir agora precisa de um wrapper
                    if col_b2.button("Excluir 🗑️", key=f"del_{peca.id}", type="secondary", use_container_width=True):
                        if excluir_peca_db(peca):
                            st.toast(f"Peça '{peca.tipo_peca}' excluída!")
                            st.session_state.inventario = [p for p in st.session_state.inventario if p.id != peca.id]
                            st.rerun()
                        else:
                            st.error("Erro ao excluir peça.")
                            
                with col2:
                    image_url = get_public_url(peca)
                    if image_url: 
                        st.image(image_url, width=150)
                    else: 
                        st.caption("Sem foto")