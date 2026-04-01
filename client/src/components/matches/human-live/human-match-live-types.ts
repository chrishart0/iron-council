import type {
  PlayerMatchEnvelope,
  PublicMatchDetailResponse,
  ResourceType,
  TreatyAction,
  TreatyType,
  UpgradeTrack
} from "../../../lib/types";

export type MatchDetailState =
  | {
      status: "loading";
      match: null;
      errorMessage: null;
    }
  | {
      status: "ready";
      match: PublicMatchDetailResponse;
      errorMessage: null;
    }
  | {
      status: "error";
      match: null;
      errorMessage: string;
    };

export type LiveConnectionState =
  | {
      status: "idle" | "connecting";
      envelope: null;
      message: string | null;
    }
  | {
      status: "live";
      envelope: PlayerMatchEnvelope;
      message: string | null;
    }
  | {
      status: "not_live";
      envelope: PlayerMatchEnvelope | null;
      message: string;
    };

export type MovementDraft = {
  armyId: string;
  destination: string;
};

export type RecruitmentDraft = {
  city: string;
  troops: string;
};

export type UpgradeDraft = {
  city: string;
  track: UpgradeTrack;
  targetTier: string;
};

export type TransferDraft = {
  to: string;
  resource: ResourceType;
  amount: string;
};

export type OrderDraftState = {
  movements: MovementDraft[];
  recruitment: RecruitmentDraft[];
  upgrades: UpgradeDraft[];
  transfers: TransferDraft[];
};

export type MapSelection =
  | { kind: "city"; cityId: string }
  | { kind: "army"; armyId: string };

export type SubmissionFeedback =
  | {
      status: "idle";
    }
  | {
      status: "submitting";
    }
  | {
      status: "success";
      message: string;
    }
  | {
      status: "error";
      message: string;
      code: string;
      statusCode: number;
    };

export type LiveMessagingChannel = "world" | "direct" | "group";

export type MessageDraftState = {
  channel: LiveMessagingChannel;
  directRecipientId: string;
  groupChatId: string;
  content: string;
};

export type GroupChatCreateDraftState = {
  name: string;
  selectedInviteeIds: string[];
};

export type AsyncSubmissionFeedback =
  | {
      status: "idle";
    }
  | {
      status: "submitting";
    }
  | {
      status: "success";
      message: string;
      details?: string[];
    }
  | {
      status: "error";
      message: string;
      code: string;
      statusCode: number;
    };

export type TreatyDraftState = {
  action: TreatyAction;
  treatyType: TreatyType;
  counterpartyId: string;
};

export type AllianceDraftState = {
  action: "create" | "join" | "leave";
  name: string;
  allianceId: string;
};
