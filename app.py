# --- app.py (Fase 12.10 - Ficheiro Único Estável) ---
# Todo o código está neste ficheiro. Sem 'utils.py' ou 'pages/'.

import streamlit as st
from datetime import date
import json
from fpdf import FPDF
import os 
import uuid
from PIL import Image
from supabase import create_client, Client
import io
from streamlit_url_fragment import get_fragment 
from gotrue.types import UserAttributes 

# --- Configuração da Página (Topo do Script) ---
st.set_page_config(page_title="BAL Cerâmica Studio", layout="wide", page_icon="🏺")

# --- V12.10: INICIALIZAÇÃO DE ESTADO ---
# Inicializa todos os estados primeiro
if 'user' not in st.session_state:
    st.session_state.user = None
if 'session' not in st.session_state:
    st.session_state.session = None
if 'supabase_client' not in st.session_state:
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


# --- V12.10: INICIALIZAÇÃO DO CLIENTE SUPABASE ---
# Só inicializa o cliente UMA VEZ
if st.session_state.supabase_client is None:
    try:
        SUPABASE_URL = st.secrets["supabase_url_v10"]["supabase_url"]
        SUPABASE_KEY = st.secrets["supabase_key_v10"]["supabase_key"]
    except (KeyError, FileNotFoundError):
        SUPABASE_URL = "https://ejbrasgtsgcmgheoonwy.supabase.co"
        SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYnJhc2d0c2djbWdoZW9vbnd5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI4NzE5NjksImV4cCI6MjA3ODQ0Nzk2OX0.Y9WIDBF_nyBt334QzRysZ7xA-Oj6-GqS4OrY94EgU48"
    
    # Cria o cliente e guarda-o no session_state
    st.session_state.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define a variável local 'supabase' para o resto do script
supabase = st.session_state.supabase_client

# Define a sessão (se ela já existir no cache do navegador)
if st.session_state.session:
    try:
        supabase.auth.set_session(
            st.session_state.session['access_token'], 
            st.session_state.session['refresh_token']
        )
    except Exception as e:
        st.error(f"Erro ao revalidar sessão: {e}")
        st.session_state.user = None
        st.session_state.session = None


NOME_BUCKET_FOTOS = "fotos-pecas"

# --- Parte 3: A "Classe" Peca (V10.2) ---
class Peca:
    """O "molde" para cada peça de cerâmica (V10.2)"""
    
    def __init__(self, data_producao, nome_pessoa, tipo_peca, peso_kg, altura_cm, largura_cm, profundidade_cm, 
                 tipo_argila='nenhuma', preco_argila_propria=0.0, 
                 image_path=None, peca_id=None, 
                 atelie_id=None):
        
        self.id = peca_id if peca_id else str(uuid.uuid4())
        self.atelie_id = atelie_id
        self.data_producao = data_producao
        self.nome_pessoa = nome_pessoa
        self.tipo_peca = tipo_peca
        self.peso_kg = float(peso_kg)
        self.altura_cm = float(altura_cm)
        self.largura_cm = float(largura_cm)
        self.profundidade_cm = float(profundidade_cm)
        self.tipo_argila = tipo_argila
        self.preco_argila_propria = float(preco_argila_propria) if self.tipo_argila == 'propria' else 0.0
        self.data_registro = date.today().strftime("%d/%m/%Y")
        self.image_path = image_path
        
        self.custo_argila = 0.0
        self.custo_biscoito = 0.0
        self.custo_esmalte = 0.0
        self.total = 0.0

    def recalcular_custos(self, precos):
        """Calcula os custos com base nos preços do ateliê."""
        if self.tipo_argila == 'atelie':
            self.custo_argila = self.peso_kg * precos['argila_kg']
        elif self.tipo_argila == 'propria':
            self.custo_argila = self.peso_kg * self.preco_argila_propria
        else:
            self.custo_argila = 0.0
        self.custo_biscoito = self.peso_kg * precos['biscoito_kg']
        volume_cm3 = self.altura_cm * self.largura_cm * self.profundidade_cm
        self.custo_esmalte = volume_cm3 * precos['esmalte_cm3']
        self.total = self.custo_biscoito + self.custo_esmalte + self.custo_argila

    def to_dict(self):
        return {
            "id": self.id, "atelie_id": self.atelie_id, "data_producao": self.data_producao,
            "nome_pessoa": self.nome_pessoa, "tipo_peca": self.tipo_peca, "peso_kg": self.peso_kg,
            "altura_cm": self.altura_cm, "largura_cm": self.largura_cm, "profundidade_cm": self.profundidade_cm,
            "tipo_argila": self.tipo_argila, "preco_argila_propria": self.preco_argila_propria,
            "data_registro": self.data_registro, "image_path": self.image_path,
            "custo_argila": self.custo_argila, "custo_biscoito": self.custo_biscoito,
            "custo_esmalte": self.custo_esmalte, "total": self.total
        }

    @classmethod
    def from_dict(cls, data_dict):
        peca = cls(
            peca_id=data_dict.get('id'), atelie_id=data_dict.get('atelie_id'),
            data_producao=data_dict.get('data_producao'), nome_pessoa=data_dict.get('nome_pessoa'),
            tipo_peca=data_dict.get('tipo_peca'),
            peso_kg=float(data_dict.get('peso_kg', 0)), altura_cm=float(data_dict.get('altura_cm', 0)),
            largura_cm=float(data_dict.get('largura_cm', 0)), profundidade_cm=float(data_dict.get('profundidade_cm', 0)),
            tipo_argila=data_dict.get('tipo_argila', 'nenhuma'), preco_argila_propria=float(data_dict.get('preco_argila_propria', 0)),
            image_path=data_dict.get('image_path')
        )
        peca.custo_argila = float(data_dict.get('custo_argila', 0))
        peca.custo_biscoito = float(data_dict.get('custo_biscoito', 0))
        peca.custo_esmalte = float(data_dict.get('custo_esmalte', 0))
        peca.total = float(data_dict.get('total', 0))
        return peca

# --- Parte 4: Funções de Dados (V11.0) ---

# --- Funções de Callback para gerir o estado da página de Inventário ---
def set_estado_inventario_lista():
    st.session_state.pagina_inventario_estado = 'lista'

def set_estado_inventario_adicionar():
    st.session_state.pagina_inventario_estado = 'adicionar'

def set_estado_inventario_editar(peca_id):
    st.session_state.pagina_inventario_estado = peca_id # Guarda o ID da peça a editar

# --- Função de Perfil (Crucial) ---
def verificar_ou_criar_perfil(user):
    """Garante que um utilizador (de email ou Google) tem um perfil em public.profiles."""
    try:
        # 1. Verifica se o perfil já existe
        profile_response = supabase.table('profiles').select('id').eq('id', user['id']).execute()
        
        # 2. Se não existe, cria um
        if not profile_response.data:
            supabase.table('profiles').insert({
                'id': user['id'],
                'email': user['email']
            }).execute()
            print(f"Perfil criado para {user['email']}")
        
    except Exception as e:
        # Ignora o erro se o perfil já existir (unique constraint)
        if "unique constraint" not in str(e):
            st.warning(f"Não foi possível verificar/criar o perfil: {e}")

# --- Funções de Dados Normais ---
def carregar_lista_atelies():
    """Busca os ateliês, nomes, roles E PREÇOS dos quais o utilizador é membro."""
    try:
        user_id = st.session_state.user['id']
        query_select = """
            atelie_id, 
            role, 
            atelies(
                id, 
                nome_atelie, 
                preco_biscoito_kg, 
                preco_esmalte_cm3, 
                preco_argila_kg
            )
        """
        response = supabase.table('membros_atelie') \
            .select(query_select) \
            .eq('user_id', user_id) \
            .execute()
        
        lista_formatada = []
        if response.data:
            for item in response.data:
                if item.get('atelies'): 
                    lista_formatada.append({
                        "id": item['atelies']['id'],
                        "nome_atelie": item['atelies']['nome_atelie'],
                        "role": item['role'],
                        "precos": {
                            "biscoito_kg": item['atelies']['preco_biscoito_kg'],
                            "esmalte_cm3": item['atelies']['preco_esmalte_cm3'],
                            "argila_kg": item['atelies']['preco_argila_kg']
                        }
                    })
                
        st.session_state.lista_atelies = lista_formatada
        return lista_formatada
    except Exception as e:
        st.error(f"Erro ao carregar lista de ateliês: {e}")
        return []

def carregar_dados():
    if not st.session_state.atelie_selecionado_id:
        st.error("Erro: Nenhum ateliê selecionado.")
        return []
    try:
        response = supabase.table('pecas').select('*') \
            .eq('atelie_id', st.session_state.atelie_selecionado_id) \
            .order('created_at', desc=True).execute()
        dados = response.data
        if dados:
            return [Peca.from_dict(d) for d in dados]
    except Exception as e:
        if "JWT" in str(e): return []
        st.error(f"Erro ao carregar dados: {e}")
    return []

def salvar_nova_peca(nova_peca: Peca, uploaded_file):
    atelie_id = st.session_state.atelie_selecionado_id
    if not atelie_id:
        st.error("Nenhum ateliê selecionado para salvar a peça.")
        return False
        
    nova_peca.atelie_id = atelie_id
    
    if uploaded_file is not None:
        try:
            extensao = os.path.splitext(uploaded_file.name)[1]
            image_storage_path = f"{atelie_id}/{nova_peca.id}{extensao}" 
            file_bytes = uploaded_file.getvalue()
            supabase.storage.from_(NOME_BUCKET_FOTOS).upload(
                path=image_storage_path, file=file_bytes,
                file_options={"content-type": uploaded_file.type, "upsert": "true"}
            )
            nova_peca.image_path = f"{nova_peca.id}{extensao}" # Salva só o nome do ficheiro
        except Exception as e:
            st.error(f"Erro ao fazer upload da imagem: {e}")
            return False
    try:
        dados_para_salvar = nova_peca.to_dict()
        supabase.table('pecas').insert(dados_para_salvar).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados da peça: {e}")
        if nova_peca.image_path:
            path_to_remove = f"{atelie_id}/{nova_peca.image_path}"
            supabase.storage.from_(NOME_BUCKET_FOTOS).remove([path_to_remove])
        return False

def excluir_peca_db(peca: Peca):
    if peca.image_path:
        try:
            path_to_remove = f"{peca.atelie_id}/{peca.image_path}"
            supabase.storage.from_(NOME_BUCKET_FOTOS).remove([path_to_remove])
        except Exception as e:
            st.warning(f"Erro ao excluir a foto: {e}")
    try:
        supabase.table('pecas').delete().eq('id', peca.id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao excluir os dados da peça: {e}")
        return False

# --- V10.8: FUNÇÃO ATUALIZAR PEÇA ---
def atualizar_peca_db(peca_obj_atualizado: Peca, new_file):
    """Atualiza uma peça existente na DB e lida com a foto."""
    try:
        # 1. Lidar com a foto (se houver uma nova)
        if new_file is not None:
            # 1a. Apaga a foto antiga, se existir
            if peca_obj_atualizado.image_path:
                old_path = f"{peca_obj_atualizado.atelie_id}/{peca_obj_atualizado.image_path}"
                try:
                    supabase.storage.from_(NOME_BUCKET_FOTOS).remove([old_path])
                except Exception as e:
                    st.warning(f"Não foi possível apagar a foto antiga (ela pode não existir): {e}")
            
            # 1b. Upload da nova foto
            extensao = os.path.splitext(new_file.name)[1]
            novo_image_path_nome = f"{peca_obj_atualizado.id}{extensao}" # Nome do ficheiro é a ID da peça
            novo_image_storage_path = f"{peca_obj_atualizado.atelie_id}/{novo_image_path_nome}"
            
            file_bytes = new_file.getvalue()
            supabase.storage.from_(NOME_BUCKET_FOTOS).upload(
                path=novo_image_storage_path, file=file_bytes,
                file_options={"content-type": new_file.type, "upsert": "true"}
            )
            peca_obj_atualizado.image_path = novo_image_path_nome # Salva só o nome do ficheiro
        
        # 2. Recalcular custos com base nos novos dados
        peca_obj_atualizado.recalcular_custos(st.session_state.precos_atelie)
        
        # 3. Preparar dados e salvar na DB
        dados_para_atualizar = peca_obj_atualizado.to_dict()
        # 'id' não deve ser atualizado, nem o atelie_id
        dados_para_atualizar.pop('id', None) 
        dados_para_atualizar.pop('atelie_id', None)
        
        supabase.table('pecas').update(dados_para_atualizar).eq('id', peca_obj_atualizado.id).execute()
        
        # 4. Atualizar o cache local (session_state)
        st.session_state.inventario = [
            peca_obj_atualizado if p.id == peca_obj_atualizado.id else p 
            for p in st.session_state.inventario
        ]
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar a peça: {e}")
        return False

# --- V10.6: Função ---
def handle_remover_membro(user_id_para_remover, email_membro):
    """Remove um membro do ateliê selecionado."""
    try:
        atelie_id = st.session_state.atelie_selecionado_id
        
        supabase.table('membros_atelie') \
            .delete() \
            .eq('user_id', user_id_para_remover) \
            .eq('atelie_id', atelie_id) \
            .execute()
        
        st.success(f"O utilizador {email_membro} foi removido do ateliê.")
        st.session_state.lista_membros = []
        st.rerun()
        
    except Exception as e:
        st.error(f"Erro ao remover membro: {e}")

# --- Parte 5: Funções de Geração (V10.1 - Corrigido) ---
def get_public_url(peca: Peca):
    if not peca.image_path:
        return None
    try:
        path_to_image = f"{peca.atelie_id}/{peca.image_path}"
        response = supabase.storage.from_(NOME_BUCKET_FOTOS).create_signed_url(path_to_image, 60)
        return response['signedURL']
    except Exception as e:
        st.error(f"Erro ao gerar URL da imagem: {e}")
        return None

def gerar_relatorio_pdf(lista_de_pecas):
    if not lista_de_pecas: return None, None # V12.9: Retorna tuplo
    custo_geral_total = 0.0
    totais_por_pessoa = {}
    for peca in lista_de_pecas:
        nome, total_peca = peca.nome_pessoa, peca.total
        custo_geral_total += total_peca
        total_anterior_pessoa = totais_por_pessoa.get(nome, 0.0)
        totais_por_pessoa[nome] = total_anterior_pessoa + total_peca
    
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page(); pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Relatorio de Producao do Atelie', ln=True, align='C'); pdf.ln(5)
    
    for peca in lista_de_pecas:
        pdf.set_font('Arial', '', 10); 
        image_url = get_public_url(peca)
        y_antes = pdf.get_y()
        if image_url:
            try:
                pdf.image(image_url, x=170, y=y_antes, w=30, h=25); pdf.set_auto_page_break(auto=False, margin=0)
            except Exception as e: print(f"Erro ao adicionar imagem URL ao PDF: {e}")
        
        pdf.set_font('Arial', 'B', 10)
        # --- V12.9: Garante que os dados são strings antes de concatenar ---
        linha1 = f"Data Prod.: {str(peca.data_producao)} | Pessoa: {str(peca.nome_pessoa)} | Peca: {str(peca.tipo_peca)}"
        # --- V12.9: REMOVIDO o .encode/.decode ---
        pdf.multi_cell(160, 5, linha1, border=0, ln=True)
        
        pdf.set_font('Arial', '', 10)
        custo_biscoito_str = f"R$ {peca.custo_biscoito:.2f}".replace('.', ',')
        custo_esmalte_str = f"R$ {peca.custo_esmalte:.2f}".replace('.', ',')
        custo_argila_str = f"R$ {peca.custo_argila:.2f}".replace('.', ',')
        linha2 = f"  Custos: Queima de biscoito({custo_biscoito_str}), Queima de esmalte({custo_esmalte_str}), Argila({custo_argila_str})"
        pdf.multi_cell(160, 5, linha2, border=0, ln=True)
        
        total_peca_str = f"R$ {peca.total:.2f}".replace('.', ',')
        linha3 = f"  >> Total da Peca: {total_peca_str}"
        pdf.multi_cell(160, 5, linha3, border=0, ln=True)
        
        linha4 = f"  (Registrado em: {str(peca.data_registro)})"
        pdf.multi_cell(160, 5, linha4, border=0, ln=True)
        
        y_depois_texto = pdf.get_y(); y_depois_imagem = y_antes + 25 
        pdf.set_y(max(y_depois_texto, y_depois_imagem))
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y()); pdf.ln(3)
        
    pdf.ln(10); pdf.set_font('Arial', 'B', 12); pdf.cell(0, 5, '--- RESUMO TOTAL ---', ln=True, align='C')
    pdf.set_font('Arial', '', 10); pdf.cell(0, 5, f"Total de pecas: {len(lista_de_pecas)}", ln=True)
    custo_geral_str = f"R$ {custo_geral_total:.2f}".replace('.', ',')
    pdf.cell(0, 5, f"CUSTO GERAL TOTAL: {custo_geral_str}", ln=True); pdf.ln(5)
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 5, '--- RESUMO POR PESSOA ---', ln=True, align='C')
    pdf.set_font('Arial', '', 10)
    
    for nome, total_pessoa in totais_por_pessoa.items():
        total_pessoa_str = f"R$ {total_pessoa:.2f}".replace('.', ',')
        linha_total_pessoa = f"  {str(nome)}: {total_pessoa_str}"
        pdf.multi_cell(0, 5, linha_total_pessoa, border=0, ln=True) # Usei multi_cell para segurança
        
    nome_arquivo_pdf = f"relatorio_atelie_{date.today().strftime('%Y-%m-%d')}.pdf"
    try:
        # --- V12.9: A forma correta de "output" para o Streamlit ---
        # Salva o PDF como bytes na memória
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        return pdf_bytes, nome_arquivo_pdf
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}"); 
        return None, None


# --- V12.10: CSS Robusto para esconder a barra lateral ---
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
            
            # --- V12.10: LÓGICA DA SIDEBAR CORRIGIDA ---
            # Primeiro, processamos os botões
            trocar_atelie = st.sidebar.button("Trocar de Ateliê")
            logout = st.sidebar.button("Terminar Sessão (Logout)")

            # Depois, desenhamos o resto
            st.sidebar.title(f"{st.session_state.atelie_selecionado_nome}")
            st.sidebar.write(f"Olá, {st.session_state.user['email']}")
            st.sidebar.markdown(f"**Sua Função:** `{st.session_state.role_atual}`")
            st.sidebar.divider()
            
            try:
                SUPABASE_URL_CHECK = st.secrets["supabase_url_v10"]["supabase_url"]
            except (KeyError, FileNotFoundError):
                st.sidebar.warning("A usar chaves locais.")

            # Agora, executamos as ações dos botões
            if trocar_atelie:
                # Limpa apenas os dados do ateliê, mantém o login
                st.session_state.atelie_selecionado_id = None
                st.session_state.atelie_selecionado_nome = None
                st.session_state.role_atual = None
                st.session_state.inventario = []
                st.session_state.lista_membros = []
                st.session_state.precos_atelie = {}
                st.session_state.pagina_inventario_estado = 'lista'
                st.rerun()
            
            if logout:
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            
            # --- V12.10: Redirecionamento Corrigido ---
            # Descobre qual é a página atual (hack do Streamlit)
            # Se for "app", redireciona. Se já for outra página, fica quieto.
            try:
                # Esta é uma forma instável, mas comum, de verificar a página atual
                current_page_script_hash = st.session_state.get('page_script_hash', '')
                is_main_app_page = 'app.py' in st.runtime.scriptrunner.get_script_run_ctx().script_path
            except Exception:
                is_main_app_page = False # Assume que não é a página principal se falhar

            # Se o utilizador está na app.py (e logado), redireciona
            if is_main_app_page:
                 st.switch_page("pages/1_Inventário.py")