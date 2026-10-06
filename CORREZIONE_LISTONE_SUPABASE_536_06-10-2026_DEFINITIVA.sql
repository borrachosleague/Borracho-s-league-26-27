-- CORREZIONE DEFINITIVA LISTONE SUPABASE - 06/10/2026
-- 599 -> 536: elimina 64 fuori-lista pending e aggiunge Obric (DIF).
-- Non modifica rose, prezzi, crediti, login, deleghe o impostazioni.
-- Eseguire tutto in Supabase -> SQL Editor. NESSUN BAT.

BEGIN;

CREATE TEMP TABLE fuori_lista(nome text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO fuori_lista(nome) VALUES
    ('Ahanor'),
    ('Albarracin'),
    ('Angelino'),
    ('Anjorin'),
    ('Athekame'),
    ('Azon'),
    ('Bjarkason'),
    ('Borrelli'),
    ('Buksa'),
    ('Camara A.'),
    ('Ciocci'),
    ('Circati'),
    ('Corrado'),
    ('Cuenca A.'),
    ('Dallinga'),
    ('David'),
    ('Delli Carri'),
    ('Di Gregorio'),
    ('Dia'),
    ('Djimsiti'),
    ('El Aynaoui'),
    ('Fofana Y.'),
    ('Fruchtl'),
    ('Gelli J.'),
    ('Gimenez'),
    ('Gutierrez'),
    ('Iannoni'),
    ('Koutsoupias'),
    ('Kuhn'),
    ('Leao'),
    ('Lukaku'),
    ('Macchioni'),
    ('Martin'),
    ('Matturro'),
    ('Miretti'),
    ('Missori'),
    ('Mlacic'),
    ('Morata'),
    ('Moro L.'),
    ('Mutandwa'),
    ('Nkunku'),
    ('Norton-Cuffy'),
    ('Ondrejka'),
    ('Oyono J.'),
    ('Paleari'),
    ('Patric'),
    ('Pedersen'),
    ('Perez M.'),
    ('Perin'),
    ('Petagna'),
    ('Piana'),
    ('Pizzignacco'),
    ('Prati'),
    ('Raterink'),
    ('Ratkov'),
    ('Romagnoli'),
    ('Rossi F.'),
    ('Samooja'),
    ('Sorensen O.'),
    ('Suzuki'),
    ('Vaz'),
    ('Vismara'),
    ('Vogliacco'),
    ('Zappa');

-- Sicurezza 1: tutti e 64 devono esistere.
DO $$
DECLARE n integer;
BEGIN
  SELECT count(*) INTO n
  FROM public.players p
  JOIN fuori_lista f ON lower(trim(p.nome)) = lower(trim(f.nome));
  IF n <> 64 THEN
    RAISE EXCEPTION 'STOP: trovati % dei 64 giocatori fuori-lista attesi. Nessuna modifica applicata.', n;
  END IF;
END
$$;

-- Sicurezza 2: nessuno dei 64 può essere assegnato/non pending.
DO $$
DECLARE n integer;
BEGIN
  SELECT count(*) INTO n
  FROM public.players p
  JOIN fuori_lista f ON lower(trim(p.nome)) = lower(trim(f.nome))
  WHERE p.stato <> 'pending' OR p.vincitore IS NOT NULL;
  IF n <> 0 THEN
    RAISE EXCEPTION 'STOP: % giocatori fuori-lista risultano assegnati/non pending. Nessuna modifica applicata.', n;
  END IF;
END
$$;

DELETE FROM public.players p
USING fuori_lista f
WHERE lower(trim(p.nome)) = lower(trim(f.nome))
  AND p.stato = 'pending'
  AND p.vincitore IS NULL;

INSERT INTO public.players (nome, ruolo, stato, vincitore, prezzo_finale, in_serie_a)
SELECT 'Obric', 'DIF', 'pending', NULL, NULL, true
WHERE NOT EXISTS (
  SELECT 1 FROM public.players WHERE lower(trim(nome)) = 'obric'
);

-- Sicurezza 3: conteggi finali attesi.
DO $$
DECLARE tot integer; sld integer; pnd integer;
BEGIN
  SELECT count(*),
         count(*) FILTER (WHERE stato='sold'),
         count(*) FILTER (WHERE stato='pending')
  INTO tot, sld, pnd
  FROM public.players;

  IF tot <> 536 OR sld <> 250 OR pnd <> 286 THEN
    RAISE EXCEPTION 'STOP: conteggi finali inattesi: totale %, sold %, pending %. Nessuna modifica applicata.', tot, sld, pnd;
  END IF;
END
$$;

COMMIT;

SELECT stato, count(*) AS quanti
FROM public.players
GROUP BY stato
ORDER BY stato;

SELECT count(*) AS totale_giocatori FROM public.players;

SELECT id, nome, ruolo, stato, in_serie_a
FROM public.players
WHERE lower(trim(nome)) IN ('lukaku','obric')
ORDER BY nome;
