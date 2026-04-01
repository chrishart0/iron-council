import type { PlayerMatchEnvelope, PublicMatchDetailResponse } from "../../../lib/types";

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
