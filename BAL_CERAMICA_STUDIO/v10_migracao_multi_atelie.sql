{\rtf1\ansi\ansicpg1252\cocoartf2639
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\froman\fcharset0 Times-Roman;}
{\colortbl;\red255\green255\blue255;\red0\green0\blue0;}
{\*\expandedcolortbl;;\cssrgb\c0\c0\c0;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\deftab720
\pard\pardeftab720\partightenfactor0

\f0\fs24 \cf0 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 -- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---\
-- FASE 10.0: SCRIPT DE MIGRA\'c7\'c3O PARA MULTI-ATELIE (v2 - Corre\'e7\'e3o NOT NULL)\
-- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---\
\
-- --- --- --- --- --- --- --- --- --- --- --- --- --- ---\
-- Parte 1: Criar as novas tabelas de Ateli\'eas e Membros\
-- --- --- --- --- --- --- --- --- --- --- --- --- --- ---\
\
-- Tabela para guardar os ateli\'eas\
CREATE TABLE public.atelies (\
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,\
  created_at TIMESTAMPTZ DEFAULT NOW(),\
  nome_atelie TEXT NOT NULL -- <-- CORRIGIDO AQUI\
);\
COMMENT ON TABLE public.atelies IS 'Guarda os nomes dos ateli\'eas (ex: Atelie Urucum)';\
\
-- Tabela "pivot" que liga utilizadores (auth.users) a ateli\'eas (public.atelies)\
CREATE TABLE public.membros_atelie (\
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,\
  created_at TIMESTAMPTZ DEFAULT NOW(),\
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,\
  atelie_id UUID REFERENCES public.atelies(id) ON DELETE CASCADE NOT NULL,\
  \
  -- Garante que um utilizador n\'e3o pode estar duas vezes no mesmo ateli\'ea\
  UNIQUE(user_id, atelie_id) \
);\
COMMENT ON TABLE public.membros_atelie IS 'Tabela de liga\'e7\'e3o que define quais utilizadores pertencem a quais ateli\'eas.';\
\
-- --- --- --- --- --- --- --- --- --- --- --- --- --- ---\
-- Parte 2: Migrar a tabela "pecas" (V9 -> V10)\
-- --- --- --- --- --- --- --- --- --- --- --- --- --- ---\
\
-- Primeiro, recriamos a tabela 'pecas' da V9.4\
CREATE TABLE public.pecas (\
  id UUID PRIMARY KEY,\
  user_id UUID REFERENCES auth.users(id), -- A coluna que vamos trocar\
  created_at TIMESTAMPTZ DEFAULT NOW(),\
  data_producao TEXT,\
  nome_pessoa TEXT,\
  tipo_peca TEXT,\
  peso_kg FLOAT,\
  altura_cm FLOAT,\
  largura_cm FLOAT,\
  profundidade_cm FLOAT,\
  tipo_argila TEXT,\
  preco_argila_propria FLOAT,\
  data_registro TEXT,\
  image_path TEXT,\
  custo_argila FLOAT,\
  custo_biscoito FLOAT,\
  custo_esmalte FLOAT,\
  total FLOAT\
);\
COMMENT ON TABLE public.pecas IS 'Tabela de pe\'e7as V9.1 (tempor\'e1ria)';\
\
-- AGORA, COME\'c7A A MIGRA\'c7\'c3O\
\
-- 1. Desativar RLS temporariamente para fazer as altera\'e7\'f5es\
ALTER TABLE public.pecas DISABLE ROW LEVEL SECURITY;\
\
-- 2. Remover a coluna antiga que ligava a pe\'e7a a UM utilizador\
ALTER TABLE public.pecas DROP COLUMN user_id;\
\
-- 3. Adicionar a nova coluna que liga a pe\'e7a a UM ateli\'ea\
ALTER TABLE public.pecas\
ADD COLUMN atelie_id UUID REFERENCES public.atelies(id) ON DELETE SET NULL; -- Se o ateli\'ea for apagado, a pe\'e7a fica "\'f3rf\'e3"\
COMMENT ON COLUMN public.pecas.atelie_id IS 'Liga a pe\'e7a a um ateli\'ea, em vez de um utilizador.';\
\
-- --- --- --- --- --- --- --- --- --- --- --- --- --- ---\
-- Parte 3: Apagar TODAS as pol\'edticas de seguran\'e7a (RLS) antigas\
-- --- --- --- --- --- --- --- --- --- --- --- --- --- ---\
\
-- Apagar as pol\'edticas da tabela 'pecas' (com os nomes que voc\'ea me passou)\
DROP POLICY IF EXISTS "Permitir utilizador ver as suas pr\'f3prias pe\'e7as" ON public.pecas;\
DROP POLICY IF EXISTS "Permitir utilizador criar as suas pr\'f3prias pe\'e7as" ON public.pecas;\
DROP POLICY IF EXISTS "Permitir utilizador atualizar as suas pr\'f3prias pe\'e7as" ON public.pecas;\
DROP POLICY IF EXISTS "Permitir utilizador excluir as suas pr\'f3prias pe\'e7as" ON public.pecas;\
\
-- --- --- --- --- --- --- --- --- --- --- --- --- --- ---\
-- Parte 4: Criar as NOVAS pol\'edticas (RLS) da V10\
-- --- --- --- --- --- --- --- --- --- --- --- --- --- ---\
\
-- FUN\'c7\'c3O AJUDANTE:\
-- Cria uma fun\'e7\'e3o SQL que verifica se um utilizador \'e9 membro de um ateli\'ea espec\'edfico.\
CREATE OR REPLACE FUNCTION public.is_membro_do_atelie(p_atelie_id UUID)\
RETURNS BOOLEAN\
LANGUAGE SQL\
SECURITY DEFINER\
AS $$\
  SELECT EXISTS (\
    SELECT 1\
    FROM public.membros_atelie\
    WHERE membros_atelie.atelie_id = p_atelie_id\
      AND membros_atelie.user_id = auth.uid()\
  );\
$$;\
\
-- Agora, as novas regras para a tabela 'pecas'\
\
-- 1. SELECT: Utilizadores podem VER pe\'e7as SE forem membros do ateli\'ea dessa pe\'e7a.\
CREATE POLICY "Membros podem ver pe\'e7as do seu ateli\'ea"\
ON public.pecas\
FOR SELECT USING (\
  public.is_membro_do_atelie(atelie_id)\
);\
\
-- 2. INSERT: Utilizadores podem CRIAR pe\'e7as SE o ateli\'ea que est\'e3o a associar for um dos seus.\
CREATE POLICY "Membros podem criar pe\'e7as no seu ateli\'ea"\
ON public.pecas\
FOR INSERT WITH CHECK (\
  public.is_membro_do_atelie(atelie_id)\
);\
\
-- 3. UPDATE: Utilizadores podem ATUALIZAR pe\'e7as SE forem membros do ateli\'ea dessa pe\'e7a.\
CREATE POLICY "Membros podem atualizar pe\'e7as do seu ateli\'ea"\
ON public.pecas\
FOR UPDATE USING (\
  public.is_membro_do_atelie(atelie_id)\
);\
\
-- 4. DELETE: Utilizadores podem APAGAR pe\'e7as SE forem membros do ateli\'ea dessa pe\'e7a.\
CREATE POLICY "Membros podem apagar pe\'e7as do seu ateli\'ea"\
ON public.pecas\
FOR DELETE USING (\
  public.is_membro_do_atelie(atelie_id)\
);\
\
-- 5. Ativar a RLS na tabela 'pecas'\
ALTER TABLE public.pecas ENABLE ROW LEVEL SECURITY;\
\
-- --- --- --- --- --- --- --- --- --- --- --- --- --- ---\
-- Parte 5: Migrar o Storage (Bucket 'fotos-pecas')\
-- --- --- --- --- --- --- --- --- --- --- --- --- --- ---\
\
-- 1. Criar o bucket (com o mesmo nome da V9)\
INSERT INTO storage.buckets (id, name, public)\
VALUES ('fotos-pecas', 'fotos-pecas', false)\
ON CONFLICT (id) DO NOTHING; -- N\'e3o falha se j\'e1 existir\
\
-- 2. Apagar as pol\'edticas de Storage antigas (Nomes REAIS fornecidos)\
DROP POLICY IF EXISTS "Permitir leituras p\'fablicas em fotos-pecas" ON storage.objects;\
DROP POLICY IF EXISTS "Permitir uploads an\'f3nimos em fotos-pecas" ON storage.objects;\
DROP POLICY IF EXISTS "Permitir utilizador excluir as suas fotos" ON storage.objects;\
DROP POLICY IF EXISTS "Permitir utilizador fazer upload para a sua pasta" ON storage.objects;\
DROP POLICY IF EXISTS "Permitir utilizador ver as suas fotos" ON storage.objects;\
\
-- 3. Criar NOVAS pol\'edticas de Storage V10\
\
-- Fun\'e7\'e3o ajudante para extrair o 'atelie_id' do caminho do ficheiro (ex: "atelie-uuid-123/foto.png")\
CREATE OR REPLACE FUNCTION public.get_atelie_id_from_storage_path(p_path TEXT)\
RETURNS UUID\
LANGUAGE SQL\
AS $$\
  SELECT (string_to_array(p_path, '/'))[1]::UUID;\
$$;\
\
\
-- 1. SELECT: Utilizador pode VER uma foto SE for membro do ateli\'ea (pasta) onde a foto est\'e1.\
CREATE POLICY "Membros podem ver fotos do ateli\'ea"\
ON storage.objects\
FOR SELECT USING (\
  bucket_id = 'fotos-pecas'\
  AND public.is_membro_do_atelie(\
        public.get_atelie_id_from_storage_path(name)\
      )\
);\
\
-- 2. INSERT: Utilizador pode FAZER UPLOAD de uma foto SE for membro do ateli\'ea (pasta) para onde est\'e1 a enviar.\
CREATE POLICY "Membros podem fazer upload para o ateli\'ea"\
ON storage.objects\
FOR INSERT WITH CHECK (\
  bucket_id = 'fotos-pecas'\
  AND public.is_membro_do_atelie(\
        public.get_atelie_id_from_storage_path(name)\
      )\
);\
\
-- 3. UPDATE: (Mesma l\'f3gica)\
CREATE POLICY "Membros podem atualizar fotos do ateli\'ea"\
ON storage.objects\
FOR UPDATE USING (\
  bucket_id = 'fotos-pecas'\
  AND public.is_membro_do_atelie(\
        public.get_atelie_id_from_storage_path(name)\
      )\
);\
\
-- 4. DELETE: (Mesma l\'f3gica)\
CREATE POLICY "Membros podem apagar fotos do ateli\'ea"\
ON storage.objects\
FOR DELETE USING (\
  bucket_id = 'fotos-pecas'\
  AND public.is_membro_do_atelie(\
        public.get_atelie_id_from_storage_path(name)\
      )\
);}