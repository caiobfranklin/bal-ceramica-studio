-- --- --- --- --- --- --- --- --- --- --- --- ---
-- FASE 10.1: SCRIPT DE ATUALIZAÇÃO (Adicionar Roles)
-- --- --- --- --- --- --- --- --- --- --- --- ---

-- 1. Adiciona a coluna 'role' à tabela de membros.
-- 'admin' = Pode gerir o ateliê (convidar/remover)
-- 'membro' = Pode apenas ver/criar peças
ALTER TABLE public.membros_atelie
ADD COLUMN role TEXT DEFAULT 'membro' NOT NULL;

-- 2. (Opcional, mas recomendado)
-- Cria um "index" para otimizar a busca de membros
CREATE INDEX idx_membros_atelie_user_atelie ON public.membros_atelie(user_id, atelie_id);

-- 3. (IMPORTANTE) Atualiza a RLS de 'membros_atelie'
-- Precisamos de regras para que as pessoas possam ver quem está no ateliê
ALTER TABLE public.membros_atelie ENABLE ROW LEVEL SECURITY;

-- Apaga políticas antigas (se houver)
DROP POLICY IF EXISTS "Membros podem ver outros membros do ateliê" ON public.membros_atelie;
DROP POLICY IF EXISTS "Admins podem gerir membros do ateliê" ON public.membros_atelie;

-- Nova política de SELECT:
-- Permite que um utilizador veja TODOS os membros
-- do ateliê do qual ele faz parte.
CREATE POLICY "Membros podem ver outros membros do ateliê"
ON public.membros_atelie
FOR SELECT USING (
  -- O utilizador atual (auth.uid()) deve estar na lista de membros
  -- do ateliê que está a ser consultado (atelie_id)
  public.is_membro_do_atelie(atelie_id)
);

-- Nova política de INSERT/DELETE (só para Admins)
-- Vamos criar uma função ajudante para verificar se é admin
CREATE OR REPLACE FUNCTION public.is_admin_do_atelie(p_atelie_id UUID)
RETURNS BOOLEAN
LANGUAGE SQL
SECURITY DEFINER
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.membros_atelie
    WHERE membros_atelie.atelie_id = p_atelie_id
      AND membros_atelie.user_id = auth.uid()
      AND membros_atelie.role = 'admin'
  );
$$;

-- Política de INSERT: Apenas admins podem adicionar membros
CREATE POLICY "Admins podem adicionar membros"
ON public.membros_atelie
FOR INSERT WITH CHECK (
  public.is_admin_do_atelie(atelie_id)
);

-- Política de DELETE: Apenas admins podem remover membros
CREATE POLICY "Admins podem remover membros"
ON public.membros_atelie
FOR DELETE USING (
  public.is_admin_do_atelie(atelie_id)
);
