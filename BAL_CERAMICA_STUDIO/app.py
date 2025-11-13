# --- app.py (Fase 12.9 - DEFINITIVO) ---

import streamlit as st
# --- V12.1: CONFIGURAÇÃO DA PÁGINA ---
# TEM DE SER O PRIMEIRO COMANDO STREAMLIT A SER EXECUTADO
st.set_page_config(page_title="BAL Cerâmica Studio", layout="wide", page_icon="🏺")


# --- V12.3: INICIALIZAÇÃO DO ESTADO (MOVIDO PARA O TOPO) ---
# Isto TEM de acontecer antes de importar o utils.py
if 'user' not in st.session_state:
    st.session_state.user = None
if 'session' not in st.session_state:
    st.session_state.session = None
if 'supabase_client' not in st.session_state: # <-- V12.4: Novo
    st.session_state.supabase_client = None
if 'inventario' not in st.session_state:
    st.session_state.inventario = []
if 'lista_atelies' not in st.session_state:
    st.session_state.lista_atelies = []
if 'atelie_selecionado_id' not in st.session_state:
    st.session_state.atelie_selecionado_id = None
if 'atelie_selecionado_nome' not in st.session_state:
    st.session_state.atelie_selecionado_nome = None
if 'role_atual' not in st.session_state:
    st.session_state.role_atual = None
if 'lista_membros' not in st.session_state:
    st.session_state.lista_membros = []
if 'precos_atelie' not in st.session_state:
    st.session_state.precos_atelie = {
        "biscoito_kg": 0.0,
        "esmalte_cm3": 0.0,
        "argila_kg": 0.0
    }
if 'pagina_inventario_estado' not in st.session_state:
    st.session_state.pagina_inventario_estado = 'lista'


# --- V12.3: Importações agora são seguras ---
from streamlit_url_fragment import get_fragment 
from gotrue.types import UserAttributes 
from utils import (
    # supabase, # <-- V12.4: Não importamos mais o cliente daqui
    verificar_ou_criar_perfil, 
    carregar_lista_atelies
)
from supabase import create_client, Client # V12.4: Importamos as ferramentas


# --- V12.4: INICIALIZAÇÃO DO CLIENTE SUPABASE ---
# Só inicializa o cliente UMA VEZ
if st.session_state.supabase_client is None:
    try:
        # --- V12.5: CORREÇÃO DOS SECRETS ---
        SUPABASE_URL = st.secrets["supabase_url_v10"]["supabase_url"]
        SUPABASE_KEY = st.secrets["supabase_key_v10"]["supabase_key"]
    except (KeyError, FileNotFoundError):
        SUPABASE_URL = "https://ejbrasgtsgcmgheoonwy.supabase.co"
        SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYnJhc2d0c2djbWdoZW9vbnd5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI4NzE5NjksImV4cCI6MjA3ODQ0Nzk2OX0.Y9WIDBF_nyBt334QzRysZ7xA-Oj6-GqS4OrY94EgU48"
    
    # Cria o cliente e guarda-o no session_state
    st.session_state.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Agora que o cliente existe, defina a sessão (se ela existir)
supabase = st.session_state.supabase_client # Define a variável local para o resto deste script
if st.session_state.session:
    try:
        supabase.auth.set_session(
            st.session_state.session['access_token'], 
            st.session_state.session['refresh_token']
        )
    except Exception as e:
        st.error(f"Erro ao revalidar sessão: {e}")
        # Limpa a sessão inválida
        st.session_state.user = None
        st.session_state.session = None


# --- V12.1: CSS Robusto para esconder a barra lateral ---
HIDE_SIDEBAR_CSS = """
    <style>
        /* Esconde a barra lateral principal */
        section[data-testid="stSidebar"] {
            display: none;
        }
        /* (Se o seletor acima falhar, este também tenta) */
        [data-testid="stSidebar"] {
            display: none;
        }
    </style>
"""


# --- V10.5: ROTEAMENTO (Router) ---

fragment = get_fragment() 

def parse_fragment(fragment_str):
    params = {}
    if fragment_str:
        if fragment_str.startswith("#"):
            fragment_str = fragment_str[1:]
        pairs = fragment_str.split('&')
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[key] = value
    return params

# Estado 1: O utilizador acabou de clicar no link de recuperação de senha
fragment_params = parse_fragment(fragment)
if (fragment_params.get("type") == "recovery" and 
    fragment_params.get("access_token") and 
    'password_reset_processed' not in st.session_state):
    
    st.markdown(HIDE_SIDEBAR_CSS, unsafe_allow_html=True) # Esconde sidebar
    st.title("Defina a sua Nova Senha")
    st.info("Você está a aceder através de um link de recuperação de senha. Por favor, defina uma nova senha.")
    
    access_token = fragment_params.get("access_token")
    
    try:
        supabase.auth.set_session(access_token=access_token, refresh_token="dummy_refresh_token_streamlitisweird")
    except Exception as e:
        st.error(f"Erro ao validar token: {e}")
        st.stop()

    with st.form("reset_password_form_final"):
        new_password = st.text_input("Nova Senha", type="password")
        confirm_password = st.text_input("Confirme a Nova Senha", type="password")
        submit_new_password = st.form_submit_button("Atualizar Senha")

        if submit_new_password:
            if not new_password or not confirm_password:
                st.error("Por favor, preencha ambos os campos.")
            elif new_password != confirm_password:
                st.error("As senhas não coincidem.")
            else:
                try:
                    supabase.auth.update_user(UserAttributes(password=new_password))
                    st.success("Senha atualizada com sucesso! ✅")
                    st.info("Pode fechar esta página e fazer login com a sua nova senha na página principal.")
                    st.session_state.password_reset_processed = True
                except Exception as e:
                    st.error(f"Erro ao atualizar senha: {e}")

# Estado 2: O utilizador já atualizou a senha
elif 'password_reset_processed' in st.session_state:
    st.markdown(HIDE_SIDEBAR_CSS, unsafe_allow_html=True) # Esconde sidebar
    st.success("A sua senha já foi atualizada.")
    st.info("Pode fechar esta página e fazer login.")

# Estado 3: Aplicação Normal (Login ou App Principal)
else:
    # --- PÁGINA 1: HUB DE AUTENTICAÇÃO (Login / Registo) ---
    if st.session_state.user is None:
        
        st.markdown(HIDE_SIDEBAR_CSS, unsafe_allow_html=True) # Esconde sidebar
        st.title("BAL Cerâmica Studio") 
        st.write("Bem-vindo ao sistema de gestão de custos do ateliê.")
        # LOGO_URL = "..." 
        # if LOGO_URL.startswith("https://"):
        #     st.image(LOGO_URL, width=300)
        
        st.info("Por favor, faça login ou registe uma nova conta para continuar.")
        
        tab_login, tab_registo, tab_recuperar = st.tabs(["Login", "Registar Nova Conta", "Recuperar Senha"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Palavra-passe", type="password")
                submit_login = st.form_submit_button("Entrar")
                
                if submit_login:
                    if not email or not password:
                        st.error("Por favor, preencha todos os campos.")
                    else:
                        try:
                            user_session = supabase.auth.sign_in_with_password({"email": email, "password": password})
                            st.session_state.user = user_session.user.dict()
                            st.session_state.session = user_session.session.dict()
                            verificar_ou_criar_perfil(st.session_state.user)
                            st.success("Login bem-sucedido!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro no login: {e}")

        with tab_registo:
            with st.form("signup_form"):
                email = st.text_input("Email para registo")
                password = st.text_input("Crie uma palavra-passe", type="password")
                submit_signup = st.form_submit_button("Registar")
                
                if submit_signup:
                    if not email or not password:
                        st.error("Por favor, preencha todos os campos.")
                    else:
                        try:
                            user_session = supabase.auth.sign_up({"email": email, "password": password})
                            
                            if user_session.user and user_session.session:
                                st.session_state.user = user_session.user.dict()
                                st.session_state.session = user_session.session.dict()
                                st.success("Conta criada com sucesso! A entrar...")
                                st.rerun()
                            elif user_session.user and not user_session.session:
                                st.success("Conta criada! Por favor, verifique o seu email para confirmar o registo.")
                                st.info("Após confirmar no seu email, volte e faça login.")
                            else:
                                st.error("Algo correu mal durante o registo.")
                            
                        except Exception as e:
                            if "User already registered" in str(e):
                                 st.error("Este email já está registado. Tente fazer login.")
                            else:
                                 st.error(f"Erro no registo: {e}")

        with tab_recuperar:
            st.write("Perdeu a sua palavra-passe? Insira o seu email abaixo para receber um link de recuperação.")
            with st.form("reset_password_form_v10_5", clear_on_submit=True):
                email_recuperar = st.text_input("Email da conta a recuperar")
                submit_recuperar = st.form_submit_button("Enviar link de recuperação")

                if submit_recuperar:
                    if not email_recuperar:
                        st.error("Por favor, insira um email.")
                    else:
                        try:
                            supabase.auth.reset_password_for_email(email_recuperar)
                            st.success("Link de recuperação enviado! Verifique o seu email.")
                            st.info("O email pode demorar alguns minutos e pode estar na sua pasta de Spam.")
                        except Exception as e:
                            st.error(f"Erro ao enviar email: {e}")
        
    # --- O APLICATIVO PRINCIPAL (SELECIONADOR DE ATELIÊ) ---
    else:
        # Se o utilizador está logado, mas não selecionou um ateliê
        if not st.session_state.atelie_selecionado_id:
            
            # --- V12.1: Esconde a barra lateral aqui também ---
            st.markdown(HIDE_SIDEBAR_CSS, unsafe_allow_html=True)
            
            # Limpa o estado de reset de senha se o utilizador navegar para cá
            if 'password_reset_processed' in st.session_state:
                del st.session_state.password_reset_processed
                
            if not st.session_state.lista_atelies:
                with st.spinner("A carregar seus ateliês..."):
                    carregar_lista_atelies()

            # --- Roteador de Seleção de Ateliê ---
            
            # 1. Se não tem ateliês (novo utilizador)
            if not st.session_state.lista_atelies:
                st.sidebar.title("Menu")
                st.sidebar.write(f"Olá, {st.session_state.user['email']}")
                st.warning("Parece que você ainda não é membro de nenhum ateliê.")
                st.info("Peça ao administrador de um ateliê para o convidar.")
                
                with st.form("criar_atelie_form_inicial"):
                    st.subheader("Ou crie o seu próprio ateliê:")
                    nome_novo_atelie = st.text_input("Nome do Novo Ateliê")
                    st.caption("Preços serão definidos com valores padrão e podem ser alterados depois.")
                    submit_criar_atelie = st.form_submit_button("Criar e Começar")
                    
                    if submit_criar_atelie:
                        if not nome_novo_atelie:
                            st.error("Por favor, insira um nome para o ateliê.")
                        else:
                            with st.spinner("A criar ateliê..."):
                                try:
                                    response_atelie = supabase.table('atelies').insert(
                                        {'nome_atelie': nome_novo_atelie}
                                    ).execute()
                                    novo_atelie_id = response_atelie.data[0]['id']
                                    user_id = st.session_state.user['id']
                                    supabase.table('membros_atelie').insert({
                                        'user_id': user_id, 
                                        'atelie_id': novo_atelie_id,
                                        'role': 'admin'
                                    }).execute()
                                    
                                    st.success(f"Ateliê '{nome_novo_atelie}' criado com sucesso!")
                                    st.session_state.lista_atelies = [] 
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao criar ateliê: {e}")

                if st.sidebar.button("Terminar Sessão (Logout)"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()

            # 2. Se TEM ateliês, mas nenhum está selecionado
            else:
                st.title("Selecione um Ateliê")
                st.info("Escolha um ateliê para trabalhar ou crie um novo.")
                
                st.subheader("Seus Ateliês Atuais")
                for atelie in st.session_state.lista_atelies:
                    if st.button(atelie['nome_atelie'], key=atelie['id'], use_container_width=True):
                        st.session_state.atelie_selecionado_id = atelie['id']
                        st.session_state.atelie_selecionado_nome = atelie['nome_atelie']
                        st.session_state.role_atual = atelie['role']
                        st.session_state.precos_atelie = atelie['precos']
                        # --- V12.1: Navega para a primeira página real ---
                        st.switch_page("pages/1_Inventário.py")
                
                st.divider() 

                with st.form("criar_atelie_form_selecao"):
                    st.subheader("Criar um Novo Ateliê")
                    nome_novo_atelie = st.text_input("Nome do Novo Ateliê")
                    st.caption("Você será o administrador deste novo ateliê.")
                    submit_criar_atelie = st.form_submit_button("Criar e Começar")
                    
                    if submit_criar_atelie:
                        if not nome_novo_atelie:
                            st.error("Por favor, insira um nome para o ateliê.")
                        else:
                            with st.spinner("A criar ateliê..."):
                                try:
                                    response_atelie = supabase.table('atelies').insert(
                                        {'nome_atelie': nome_novo_atelie}
                                    ).execute()
                                    novo_atelie_id = response_atelie.data[0]['id']
                                    user_id = st.session_state.user['id']
                                    supabase.table('membros_atelie').insert({
                                        'user_id': user_id, 
                                        'atelie_id': novo_atelie_id,
                                        'role': 'admin'
                                    }).execute()
                                    
                                    st.success(f"Ateliê '{nome_novo_atelie}' criado com sucesso!")
                                    st.session_state.lista_atelies = [] 
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao criar ateliê: {e}")
                
                st.sidebar.title("Menu")
                st.sidebar.write(f"Olá, {st.session_state.user['email']}")
                if st.sidebar.button("Terminar Sessão (Logout)"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()

        # 3. Se está LOGADO e um ateliê ESTÁ SELECIONADO
        else:
            # O utilizador está totalmente autenticado.
            # O Streamlit irá agora procurar e exibir os ficheiros na pasta 'pages/'.
            
            # A única coisa que o app.py faz é mostrar a barra lateral persistente.
            st.sidebar.title(f"{st.session_state.atelie_selecionado_nome}")
            st.sidebar.write(f"Olá, {st.session_state.user['email']}")
            st.sidebar.markdown(f"**Sua Função:** `{st.session_state.role_atual}`")
            
            if st.sidebar.button("Trocar de Ateliê"):
                # Limpa apenas os dados do ateliê, mantém o login
                st.session_state.atelie_selecionado_id = None
                st.session_state.atelie_selecionado_nome = None
                st.session_state.role_atual = None
                st.session_state.inventario = []
                st.session_state.lista_membros = []
                st.session_state.precos_atelie = {}
                st.session_state.pagina_inventario_estado = 'lista'
                st.rerun()
            
            st.sidebar.divider()
            
            if st.sidebar.button("Terminar Sessão (Logout)"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            
            # V12.1: Mostra um "aviso" se os secrets não estiverem configurados
            try:
                SUPABASE_URL_CHECK = st.secrets["supabase_url_v10"]["supabase_url"]
            except (KeyError, FileNotFoundError):
                st.sidebar.warning("A usar chaves locais.")
            
            # --- V12.1: Redireciona para o inventário se o utilizador visitar app.py
            # Esta é uma proteção. Se o utilizador clicar em "app" no menu,
            # ele será enviado para o inventário em vez de ver uma página em branco.
            st.switch_page("pages/1_Inventário.py")