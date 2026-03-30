export type MatchSummary = {
  match_id: string;
  status: string;
  map: string;
  tick: number;
  tick_interval_seconds: number;
  current_player_count: number;
  max_player_count: number;
  open_slot_count: number;
};

export type MatchListResponse = {
  matches: MatchSummary[];
};
