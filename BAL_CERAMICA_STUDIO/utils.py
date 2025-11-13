# --- utils.py (Fase 12.7) ---
# Este ficheiro NÃO cria mais o cliente Supabase.
# Ele assume que o cliente JÁ EXISTE em st.session_state.supabase_client

import streamlit as st
from datetime import date
import json
from fpdf import FPDF
import os 
import uuid
from PIL import Image
from supabase import create_client, Client
import io
from gotrue.types import UserAttributes 

# --- V12.4: Parte 1 (Ligação ao Supabase) REMOVIDA ---
# A ligação é agora feita no app.py

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
        supabase = st.session_state.supabase_client # V12.4
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
        supabase = st.session_state.supabase_client # V12.4
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
        supabase = st.session_state.supabase_client # V12.4
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
    supabase = st.session_state.supabase_client # V12.4
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
    supabase = st.session_state.supabase_client # V12.4
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
        supabase = st.session_state.supabase_client # V12.4
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
        supabase = st.session_state.supabase_client # V12.4
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
        supabase = st.session_state.supabase_client # V12.4
        path_to_image = f"{peca.atelie_id}/{peca.image_path}"
        response = supabase.storage.from_(NOME_BUCKET_FOTOS).create_signed_url(path_to_image, 60)
        return response['signedURL']
    except Exception as e:
        st.error(f"Erro ao gerar URL da imagem: {e}")
        return None

def gerar_relatorio_pdf(lista_de_pecas):
    if not lista_de_pecas: return None
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
        linha1 = f"Data Prod.: {peca.data_producao} | Pessoa: {peca.nome_pessoa} | Peca: {peca.tipo_peca}"
        pdf.multi_cell(160, 5, linha1.encode('latin-1', 'replace').decode('latin-1'), border=0, ln=True)
        pdf.set_font('Arial', '', 10)
        custo_biscoito_str = f"R$ {peca.custo_biscoito:.2f}".replace('.', ',')
        custo_esmalte_str = f"R$ {peca.custo_esmalte:.2f}".replace('.', ',')
        custo_argila_str = f"R$ {peca.custo_argila:.2f}".replace('.', ',')
        linha2 = f"  Custos: Queima de biscoito({custo_biscoito_str}), Queima de esmalte({custo_esmalte_str}), Argila({custo_argila_str})"
        pdf.multi_cell(160, 5, linha2.encode('latin-1', 'replace').decode('latin-1'), border=0, ln=True)
        total_peca_str = f"R$ {peca.total:.2f}".replace('.', ',')
        linha3 = f"  >> Total da Peca: {total_peca_str}"
        pdf.multi_cell(160, 5, linha3.encode('latin-1', 'replace').decode('latin-1'), border=0, ln=True)
        linha4 = f"  (Registrado em: {peca.data_registro})"
        pdf.multi_cell(160, 5, linha4.encode('latin-1', 'replace').decode('latin-1'), border=0, ln=True)
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
        linha_total_pessoa = f"  {nome}: {total_pessoa_str}"
        pdf.cell(0, 5, linha_total_pessoa.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    nome_arquivo_pdf = f"relatorio_atelie_{date.today().strftime('%Y-%m-%d')}.pdf"
    try:
        pdf.output(nome_arquivo_pdf); return nome_arquivo_pdf
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}"); return None