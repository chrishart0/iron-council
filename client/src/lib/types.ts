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

export type CompetitorKind = "human" | "agent";

export type PublicMatchRosterRow = {
  display_name: string;
  competitor_kind: CompetitorKind;
};

export type PublicMatchDetailResponse = MatchSummary & {
  roster: PublicMatchRosterRow[];
};

export type MatchLobbyCreateRequest = {
  map: "britain";
  tick_interval_seconds: number;
  max_players: number;
  victory_city_threshold: number;
  starting_cities_per_player: number;
};

export type MatchLobbyCreateResponse = MatchSummary & {
  creator_player_id: string;
};

export type MatchJoinRequest = {
  match_id: string;
};

export type MatchJoinResponse = {
  status: "accepted";
  match_id: string;
  agent_id: string;
  player_id: string;
};

export type MatchLobbyStartResponse = MatchSummary;

export type ApiErrorEnvelope = {
  error: {
    code: string;
    message: string;
  };
};

export type ResourceState = {
  food: number;
  production: number;
  money: number;
};

export type FogVisibility = "full" | "partial";
export type UnknownField = "unknown";

export type CityUpgradeState = {
  economy: number;
  military: number;
  fortification: number;
};

export type BuildingQueueItem = {
  type: string;
  tier: number;
  ticks_remaining: number;
};

export type SpectatorCityState = {
  owner: string | null;
  population: number;
  resources: ResourceState;
  upgrades: CityUpgradeState;
  garrison: number;
  building_queue: BuildingQueueItem[];
};

export type SpectatorArmyState = {
  id: string;
  owner: string;
  troops: number;
  location: string | null;
  destination: string | null;
  path: string[] | null;
  ticks_remaining: number;
};

export type SpectatorPlayerState = {
  resources: ResourceState;
  cities_owned: string[];
  alliance_id: string | null;
  is_eliminated: boolean;
};

export type VictoryState = {
  leading_alliance: string | null;
  cities_held: number;
  threshold: number;
  countdown_ticks_remaining: number | null;
};

export type SpectatorMatchState = {
  match_id: string;
  tick: number;
  cities: Record<string, SpectatorCityState>;
  armies: SpectatorArmyState[];
  players: Record<string, SpectatorPlayerState>;
  victory: VictoryState;
};

export type VisibleCityState = {
  owner: string | null;
  visibility: FogVisibility;
  population: number | UnknownField;
  resources: ResourceState | UnknownField;
  upgrades: CityUpgradeState | UnknownField;
  garrison: number | UnknownField;
  building_queue: BuildingQueueItem[] | UnknownField;
};

export type VisibleArmyState = {
  id: string;
  owner: string;
  visibility: FogVisibility;
  troops: number | UnknownField;
  location: string | null;
  destination: string | null;
  path: string[] | UnknownField | null;
  ticks_remaining: number;
};

export type PlayerMatchState = {
  match_id: string;
  tick: number;
  player_id: string;
  resources: ResourceState;
  cities: Record<string, VisibleCityState>;
  visible_armies: VisibleArmyState[];
  alliance_id: string | null;
  alliance_members: string[];
  victory: VictoryState;
};

export type WorldMessageRecord = {
  message_id: number;
  channel: "world";
  sender_id: string;
  recipient_id: null;
  tick: number;
  content: string;
};

export type DirectMessageRecord = {
  message_id: number;
  channel: "direct";
  sender_id: string;
  recipient_id: string | null;
  tick: number;
  content: string;
};

export type GroupChatRecord = {
  group_chat_id: string;
  name: string;
  member_ids: string[];
  created_by: string;
  created_tick: number;
};

export type GroupMessageRecord = {
  message_id: number;
  group_chat_id: string;
  sender_id: string;
  tick: number;
  content: string;
};

export type TreatyRecord = {
  treaty_id: number;
  player_a_id: string;
  player_b_id: string;
  treaty_type: string;
  status: string;
  proposed_by: string;
  proposed_tick: number;
  signed_tick: number | null;
  withdrawn_by: string | null;
  withdrawn_tick: number | null;
};

export type AllianceMemberRecord = {
  player_id: string;
  joined_tick: number;
};

export type AllianceRecord = {
  alliance_id: string;
  name: string;
  leader_id: string;
  formed_tick: number;
  members: AllianceMemberRecord[];
};

export type SpectatorMatchEnvelope = {
  type: "tick_update";
  data: {
    match_id: string;
    viewer_role: "spectator";
    player_id: null;
    state: SpectatorMatchState;
    world_messages: WorldMessageRecord[];
    direct_messages: DirectMessageRecord[];
    group_chats: GroupChatRecord[];
    group_messages: GroupMessageRecord[];
    treaties: TreatyRecord[];
    alliances: AllianceRecord[];
  };
};

export type PlayerMatchEnvelope = {
  type: "tick_update";
  data: {
    match_id: string;
    viewer_role: "player";
    player_id: string;
    state: PlayerMatchState;
    world_messages: WorldMessageRecord[];
    direct_messages: DirectMessageRecord[];
    group_chats: GroupChatRecord[];
    group_messages: GroupMessageRecord[];
    treaties: TreatyRecord[];
    alliances: AllianceRecord[];
  };
};
