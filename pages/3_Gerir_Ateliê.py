# --- pages/3_Gerir_Ateliê.py (Fase 12.9) ---
# Página para Admins gerirem preços e membros.

import streamlit as st

# Importa as funções necessárias do utils.py
from utils import (
    handle_remover_membro
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
    
# --- V12.9: Obter o cliente supabase do session_state ---
# (Necessário para esta página, pois ela chama a supabase diretamente)
supabase = st.session_state.supabase_client

# --- Interface da Página ---
st.header(f"Gestão do Ateliê: {st.session_state.atelie_selecionado_nome}")

if st.session_state.role_atual == 'admin':
    st.subheader("Definir Preços do Ateliê")
    with st.form("precos_form"):
        precos = st.session_state.precos_atelie
        p_biscoito = st.number_input("Preço Queima de Biscoito (por Kg)", 
                                     value=precos['biscoito_kg'], format="%.2f")
        p_esmalte = st.number_input("Preço Queima de Esmalte (por cm³)", 
                                    value=precos['esmalte_cm3'], format="%.3f")
        p_argila = st.number_input("Preço Argila do Ateliê (por Kg)", 
                                   value=precos['argila_kg'], format="%.2f")
        
        submit_precos = st.form_submit_button("Atualizar Preços")
        
        if submit_precos:
            novos_precos = {
                "preco_biscoito_kg": p_biscoito,
                "preco_esmalte_cm3": p_esmalte,
                "preco_argila_kg": p_argila
            }
            try:
                supabase.table('atelies').update(novos_precos) \
                    .eq('id', st.session_state.atelie_selecionado_id) \
                    .execute()
                
                # Atualiza o cache de preços no session_state
                st.session_state.precos_atelie = {
                    "biscoito_kg": p_biscoito,
                    "esmalte_cm3": p_esmalte,
                    "preco_argila_kg": p_argila
                }
                st.success("Preços atualizados com sucesso!")
            except Exception as e:
                st.error(f"Erro ao atualizar preços: {e}")

    st.divider()
    st.subheader("Convidar Novo Membro")
    with st.form("convidar_membro_form", clear_on_submit=True):
        email_convidado = st.text_input("Email do novo membro:")
        submit_convite = st.form_submit_button("Convidar")
        
        if submit_convite:
            if not email_convidado:
                st.error("Por favor, insira um email.")
            else:
                with st.spinner(f"A convidar {email_convidado}..."):
                    try:
                        response_profile = supabase.table('profiles').select('id') \
                            .eq('email', email_convidado).execute()
                        
                        if not response_profile.data:
                            st.error(f"Erro: Utilizador '{email_convidado}' não encontrado. Peça para ele criar uma conta primeiro.")
                        else:
                            user_id_convidado = response_profile.data[0]['id']
                            supabase.table('membros_atelie').insert({
                                'user_id': user_id_convidado,
                                'atelie_id': st.session_state.atelie_selecionado_id,
                                'role': 'membro'
                            }).execute()
                            
                            st.success(f"{email_convidado} foi adicionado ao ateliê!")
                            st.session_state.lista_membros = [] # Limpa o cache
                    
                    except Exception as e:
                        if "unique constraint" in str(e):
                            st.error(f"{email_convidado} já é membro deste ateliê.")
                        else:
                            st.error(f"Erro ao convidar: {e}")
else:
    st.info("Apenas administradores podem gerir preços e convidar novos membros.")

st.divider()

st.subheader("Membros Atuais")

# Lógica de carregamento (sempre que a lista estiver vazia)
if not st.session_state.lista_membros:
    try:
        # Chama a função RPC (que agora retorna user_id)
        response = supabase.rpc('get_membros_do_atelie', {
            'p_atelie_id': st.session_state.atelie_selecionado_id
        }).execute()
        st.session_state.lista_membros = response.data
    except Exception as e:
        st.error(f"Erro ao buscar membros: {e}")

# Substitui st.dataframe por uma lista interativa
if st.session_state.lista_membros:
    user_id_atual = st.session_state.user['id']
    
    # Cabeçalhos
    col1, col2, col3 = st.columns([2, 1, 1])
    col1.markdown("**Email**")
    col2.markdown("**Função**")
    col3.markdown("**Ação**")
    
    st.divider()

    # Lista de membros
    for membro in st.session_state.lista_membros:
        col1_m, col2_m, col3_m = st.columns([2, 1, 1])
        
        with col1_m:
            st.write(membro['email'])
        
        with col2_m:
            st.write(f"`{membro['role']}`")
        
        with col3_m:
            # Um admin só pode remover outros se for admin
            if st.session_state.role_atual == 'admin':
                # Um admin não pode remover a si mesmo
                if membro['user_id'] != user_id_atual:
                    if st.button("Remover 🗑️", key=f"remove_{membro['user_id']}", use_container_width=True):
                        handle_remover_membro(membro['user_id'], membro['email'])
                else:
                    st.caption("(Você)")
            else:
                # Membros normais não veem botões
                pass

else:
    st.warning("Não foi possível carregar a lista de membros.")