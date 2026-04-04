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
  player_id: string;
  display_name: string;
  competitor_kind: CompetitorKind;
  agent_id?: string | null;
  human_id?: string | null;
};

export type PublicMatchDetailResponse = MatchSummary & {
  roster: PublicMatchRosterRow[];
};

export type LeaderboardEntry = {
  rank: number;
  display_name: string;
  competitor_kind: CompetitorKind;
  agent_id: string | null;
  human_id: string | null;
  elo: number;
  provisional: boolean;
  matches_played: number;
  wins: number;
  losses: number;
  draws: number;
};

export type PublicCompetitorSummary = {
  display_name: string;
  competitor_kind: CompetitorKind;
  agent_id: string | null;
  human_id: string | null;
};

export type PublicLeaderboardResponse = {
  leaderboard: LeaderboardEntry[];
};

export type AgentProfileRating = {
  elo: number;
  provisional: boolean;
};

export type AgentProfileHistory = {
  matches_played: number;
  wins: number;
  losses: number;
  draws: number;
};

export type TreatyReputationSummary = {
  signed: number;
  active: number;
  honored: number;
  withdrawn: number;
  broken_by_self: number;
  broken_by_counterparty: number;
};

export type TreatyHistoryStatus =
  | "proposed"
  | "active"
  | "honored"
  | "broken_by_a"
  | "broken_by_b"
  | "withdrawn";

export type TreatyHistoryRecord = {
  match_id: string;
  counterparty_display_name: string;
  treaty_type: TreatyType;
  status: TreatyHistoryStatus;
  signed_tick: number;
  ended_tick: number | null;
  broken_by_self: boolean;
};

export type TreatyReputation = {
  summary: TreatyReputationSummary;
  history: TreatyHistoryRecord[];
};

export type PublicAgentProfileResponse = {
  agent_id: string;
  display_name: string;
  is_seeded: boolean;
  rating: AgentProfileRating;
  history: AgentProfileHistory;
  treaty_reputation: TreatyReputation;
};

export type PublicHumanProfileResponse = {
  human_id: string;
  display_name: string;
  rating: AgentProfileRating;
  history: AgentProfileHistory;
  treaty_reputation: TreatyReputation;
};

export type CompletedMatchSummary = {
  match_id: string;
  map: string;
  final_tick: number;
  tick_interval_seconds: number;
  player_count: number;
  completed_at: string;
  winning_alliance_name: string | null;
  winning_player_display_names: string[];
  winning_competitors: PublicCompetitorSummary[];
};

export type CompletedMatchSummaryListResponse = {
  matches: CompletedMatchSummary[];
};

export type MatchHistoryEntry = {
  tick: number;
};

export type PublicMatchHistoryResponse = {
  match_id: string;
  status: string;
  current_tick: number;
  tick_interval_seconds: number;
  competitors: PublicCompetitorSummary[];
  history: MatchHistoryEntry[];
};

export type ReplayFieldValue =
  | string
  | number
  | boolean
  | null
  | ReplayFieldValue[]
  | { [key: string]: ReplayFieldValue };

export type ReplayFieldRecord = {
  [key: string]: ReplayFieldValue;
};

export type MatchReplayTickResponse = {
  match_id: string;
  tick: number;
  state_snapshot: ReplayFieldRecord;
  orders: ReplayFieldRecord;
  events: ReplayFieldRecord | ReplayFieldRecord[];
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

export type OwnedApiKeySummary = {
  key_id: string;
  elo_rating: number;
  is_active: boolean;
  created_at: string;
};

export type OwnedApiKeyListResponse = {
  items: OwnedApiKeySummary[];
};

export type OwnedApiKeyCreateResponse = {
  api_key: string;
  summary: OwnedApiKeySummary;
};

export type MessageChannel = "world" | "direct";

export type UpgradeTrack = "economy" | "military" | "fortification";
export type ResourceType = "food" | "production" | "money";

export type MovementOrder = {
  army_id: string;
  destination: string;
};

export type RecruitmentOrder = {
  city: string;
  troops: number;
};

export type UpgradeOrder = {
  city: string;
  track: UpgradeTrack;
  target_tier: number;
};

export type TransferOrder = {
  to: string;
  resource: ResourceType;
  amount: number;
};

export type OrderBatch = {
  movements: MovementOrder[];
  recruitment: RecruitmentOrder[];
  upgrades: UpgradeOrder[];
  transfers: TransferOrder[];
};

export type MatchOrdersCommandRequest = {
  match_id: string;
  tick: number;
  orders: OrderBatch;
};

export type MatchMessageCreateRequest = {
  match_id: string;
  tick: number;
  channel: MessageChannel;
  recipient_id: string | null;
  content: string;
};

export type MessageAcceptanceResponse = {
  status: "accepted";
  match_id: string;
  message_id: number;
  channel: MessageChannel;
  sender_id: string;
  recipient_id: string | null;
  tick: number;
  content: string;
};

export type GroupChatMessageCreateRequest = {
  match_id: string;
  tick: number;
  content: string;
};

export type GroupChatCreateRequest = {
  match_id: string;
  tick: number;
  name: string;
  member_ids: string[];
};

export type GroupChatCreateAcceptanceResponse = {
  status: "accepted";
  match_id: string;
  group_chat: GroupChatRecord;
};

export type GroupChatMessageAcceptanceResponse = {
  status: "accepted";
  match_id: string;
  group_chat_id: string;
  message: GroupMessageRecord;
};

export type TreatyAction = "propose" | "accept" | "withdraw";
export type TreatyType = "non_aggression" | "defensive" | "trade";

export type TreatyActionRequest = {
  match_id: string;
  counterparty_id: string;
  action: TreatyAction;
  treaty_type: TreatyType;
};

export type TreatyActionAcceptanceResponse = {
  status: "accepted";
  match_id: string;
  treaty: TreatyRecord;
};

export type AllianceAction = "create" | "join" | "leave";

export type AllianceCreateRequest = {
  match_id: string;
  action: "create";
  name: string;
};

export type AllianceJoinRequest = {
  match_id: string;
  action: "join";
  alliance_id: string;
};

export type AllianceLeaveRequest = {
  match_id: string;
  action: "leave";
};

export type AllianceActionRequest =
  | AllianceCreateRequest
  | AllianceJoinRequest
  | AllianceLeaveRequest;

export type AllianceActionAcceptanceResponse = {
  status: "accepted";
  match_id: string;
  player_id: string;
  alliance: AllianceRecord;
};

export type OrderAcceptanceResponse = {
  status: "accepted";
  match_id: string;
  player_id: string;
  tick: number;
  submission_index: number;
};

export type MatchOrdersCommandEnvelopeResponse = {
  status: "accepted";
  match_id: string;
  player_id: string;
  tick: number;
  orders: OrderAcceptanceResponse | null;
  messages: unknown[];
  treaties: unknown[];
  alliance: unknown | null;
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

export type GuidedSessionGuidanceRecord = {
  guidance_id: string;
  match_id: string;
  player_id: string;
  tick: number;
  content: string;
  created_at: string;
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

export type GuidedSessionRecentActivity = {
  alliances: AllianceRecord[];
  treaties: TreatyRecord[];
};

export type OwnedAgentGuidedSessionResponse = {
  match_id: string;
  agent_id: string;
  player_id: string;
  state: PlayerMatchState;
  queued_orders: OrderBatch;
  guidance: GuidedSessionGuidanceRecord[];
  group_chats: GroupChatRecord[];
  messages: {
    world: WorldMessageRecord[];
    direct: DirectMessageRecord[];
    group: GroupMessageRecord[];
  };
  recent_activity: GuidedSessionRecentActivity;
};

export type OwnedAgentGuidanceCreateRequest = {
  match_id: string;
  tick: number;
  content: string;
};

export type OwnedAgentGuidanceAcceptanceResponse = {
  status: "accepted";
  guidance_id: string;
  match_id: string;
  agent_id: string;
  player_id: string;
  tick: number;
  content: string;
};

export type OwnedAgentOverrideCreateRequest = {
  match_id: string;
  tick: number;
  orders: OrderBatch;
};

export type OwnedAgentOverrideAcceptanceResponse = {
  status: "accepted";
  override_id: string;
  match_id: string;
  agent_id: string;
  player_id: string;
  tick: number;
  submission_index: number;
  superseded_submission_count: number;
  orders: OrderBatch;
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
