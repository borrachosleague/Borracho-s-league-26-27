-- PATCH BORRACHOS LEAGUE
-- 1) consente il rilancio sulla propria offerta
-- 2) conserva 1 credito per ogni posto rosa che restera' da riempire

CREATE OR REPLACE FUNCTION public.place_bid_as_team(
  p_player_id bigint,
  p_squadra text,
  p_importo integer
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_squadra text := p_squadra;
  v_player players%ROWTYPE;
  v_current integer := 0;
  v_current_bidder text;
  v_credits integer;
  v_count integer;
  v_limit integer;
  v_active bigint;
  v_called_at timestamptz;
  v_last_bid_at timestamptz;
  v_deadline timestamptz;
  v_total_sold integer;
  v_remaining integer;
  v_max_spendable integer;
BEGIN
  IF EXISTS(SELECT 1 FROM public.auction_state WHERE id=1 AND COALESCE(paused_preauction,false)) THEN
    RAISE EXCEPTION 'Asta sospesa: fase PRE-ASTA attiva';
  END IF;

  IF NOT public.can_manage_team(v_squadra) THEN
    RAISE EXCEPTION 'Non sei autorizzato a gestire questa squadra';
  END IF;

  IF p_importo IS NULL OR p_importo <= 0 THEN
    RAISE EXCEPTION 'Offerta non valida';
  END IF;

  SELECT active_player_id, active_called_at, last_bid_at
  INTO v_active, v_called_at, v_last_bid_at
  FROM auction_state
  WHERE id = 1 AND started_at IS NOT NULL
  FOR UPDATE;

  IF NOT FOUND OR v_active IS NULL THEN RAISE EXCEPTION 'Nessun giocatore in asta'; END IF;
  IF v_active <> p_player_id THEN RAISE EXCEPTION 'Questo giocatore non è quello attualmente in asta'; END IF;

  v_deadline = COALESCE(v_last_bid_at, v_called_at)
    + CASE WHEN v_last_bid_at IS NULL THEN interval '30 seconds' ELSE interval '10 seconds' END;
  IF now() >= v_deadline THEN RAISE EXCEPTION 'Timer scaduto'; END IF;

  SELECT * INTO v_player FROM players WHERE id=p_player_id FOR UPDATE;
  IF NOT FOUND OR v_player.stato <> 'pending' THEN RAISE EXCEPTION 'Giocatore non più disponibile'; END IF;

  SELECT importo, squadra INTO v_current, v_current_bidder
  FROM bids
  WHERE player_id=p_player_id AND squadra NOT IN ('__CALL__','__START__')
  ORDER BY id DESC LIMIT 1;

  IF p_importo <= COALESCE(v_current,0) THEN
    RAISE EXCEPTION 'Offerta minima: %', COALESCE(v_current,0)+1;
  END IF;

  -- Volutamente nessun blocco se v_current_bidder = v_squadra:
  -- una squadra puo' alzare la propria offerta.

  SELECT count(*) INTO v_count
  FROM players
  WHERE vincitore=v_squadra AND stato='sold' AND ruolo=v_player.ruolo;

  v_limit = CASE v_player.ruolo
    WHEN 'POR' THEN 3 WHEN 'DIF' THEN 8 WHEN 'CENTRO' THEN 8 WHEN 'ATT' THEN 6 ELSE 0 END;
  IF v_limit=0 THEN RAISE EXCEPTION 'Ruolo non valido: %',v_player.ruolo; END IF;
  IF v_count>=v_limit THEN RAISE EXCEPTION 'Slot % pieno',v_player.ruolo; END IF;

  SELECT crediti INTO v_credits FROM squadre WHERE nome=v_squadra FOR UPDATE;
  IF v_credits IS NULL THEN RAISE EXCEPTION 'Squadra non trovata'; END IF;

  SELECT count(*) INTO v_total_sold
  FROM players
  WHERE vincitore=v_squadra AND stato='sold';

  -- Rosa completa: 3 POR + 8 DIF + 8 CENTRO + 6 ATT = 25.
  v_remaining := GREATEST(0, 25 - v_total_sold);
  v_max_spendable := GREATEST(0, v_credits - GREATEST(0, v_remaining - 1));

  IF p_importo > v_max_spendable THEN
    RAISE EXCEPTION 'Massimo spendibile: % crediti. Devi conservare 1 credito per ogni giocatore ancora da comprare', v_max_spendable;
  END IF;

  INSERT INTO bids(player_id,squadra,importo) VALUES(p_player_id,v_squadra,p_importo);
  UPDATE auction_state SET last_bid_at=now() WHERE id=1;
END;
$$;

GRANT EXECUTE ON FUNCTION public.place_bid_as_team(bigint,text,integer) TO authenticated;
