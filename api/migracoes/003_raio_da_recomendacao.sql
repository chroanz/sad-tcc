-- O raio de busca recorta quais mercados entram na instância do problema. Duas execuções
-- com raios diferentes resolvem instâncias diferentes e, portanto, não são comparáveis.
-- Registrá-lo ao lado do peso é o que preserva a procedência do histórico usado na Fase 4.

ALTER TABLE recomendacoes
    ADD COLUMN IF NOT EXISTS parametro_raio_km NUMERIC(6,2)
        CHECK (parametro_raio_km IS NULL OR parametro_raio_km > 0);

COMMENT ON COLUMN recomendacoes.parametro_raio_km IS 'Raio em quilômetros, em linha reta a partir da origem, usado para selecionar os mercados candidatos. NULL significa sem recorte: todos os mercados cadastrados entraram.';
