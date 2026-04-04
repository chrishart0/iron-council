import { describe, expect, it } from "vitest";
import * as accountSession from "./account-session";
import * as guidedAgents from "./guided-agents";
import * as liveEnvelope from "./live-envelope";
import * as lobbyLifecycle from "./lobby-lifecycle";
import * as matchWrites from "./match-writes";
import * as publicBrowse from "./public-browse";
import * as publicContract from "./public-contract";
import * as publicHistory from "./public-history";
import * as publicProfiles from "./public-profiles";
import {
  ApiKeyLifecycleError,
  buildAuthenticatedHeaders,
  buildAuthenticatedJsonHeaders,
  buildPlayerMatchWebSocketUrl,
  buildSpectatorMatchWebSocketUrl,
  CompletedMatchesError,
  CommandSubmissionError,
  createOwnedApiKey,
  createMatchLobby,
  DiplomacySubmissionError,
  fetchCompletedMatches,
  fetchMatchReplayTick,
  fetchOwnedAgentGuidedSession,
  fetchOwnedApiKeys,
  fetchPublicAgentProfile,
  fetchPublicHumanProfile,
  fetchPublicLeaderboard,
  fetchPublicMatchDetail,
  fetchPublicMatchHistory,
  fetchPublicMatches,
  getPlayerWebSocketCloseMessage,
  GroupChatCreateError,
  GuidedAgentControlsError,
  isApiErrorEnvelope,
  isRecord,
  joinMatchLobby,
  LobbyActionError,
  MatchReplayTickError,
  MessageSubmissionError,
  parsePlayerMatchEnvelope,
  parseSpectatorMatchEnvelope,
  parseWebSocketApiErrorEnvelope,
  PublicAgentProfileError,
  PublicHumanProfileError,
  PublicLeaderboardError,
  PublicMatchDetailError,
  PublicMatchHistoryError,
  PublicMatchesError,
  resolveApiBaseUrl,
  revokeOwnedApiKey,
  startMatchLobby,
  submitAllianceAction,
  submitGroupChatCreate,
  submitGroupChatMessage,
  submitMatchMessage,
  submitMatchOrders,
  submitOwnedAgentGuidance,
  submitOwnedAgentOverride,
  submitTreatyAction
} from "../api";

describe("public api extraction seam", () => {
  it("keeps the extracted public contract helpers available through both modules", () => {
    expect(publicBrowse.fetchPublicMatches).toBe(fetchPublicMatches);
    expect(publicBrowse.fetchPublicMatchDetail).toBe(fetchPublicMatchDetail);
    expect(publicBrowse.fetchCompletedMatches).toBe(fetchCompletedMatches);
    expect(publicBrowse.PublicMatchesError).toBe(PublicMatchesError);
    expect(publicBrowse.PublicMatchDetailError).toBe(PublicMatchDetailError);
    expect(publicBrowse.CompletedMatchesError).toBe(CompletedMatchesError);
    expect(publicProfiles.fetchPublicLeaderboard).toBe(fetchPublicLeaderboard);
    expect(publicProfiles.fetchPublicAgentProfile).toBe(fetchPublicAgentProfile);
    expect(publicProfiles.fetchPublicHumanProfile).toBe(fetchPublicHumanProfile);
    expect(publicProfiles.PublicLeaderboardError).toBe(PublicLeaderboardError);
    expect(publicProfiles.PublicAgentProfileError).toBe(PublicAgentProfileError);
    expect(publicProfiles.PublicHumanProfileError).toBe(PublicHumanProfileError);
    expect(publicHistory.fetchPublicMatchHistory).toBe(fetchPublicMatchHistory);
    expect(publicHistory.fetchMatchReplayTick).toBe(fetchMatchReplayTick);
    expect(publicHistory.PublicMatchHistoryError).toBe(PublicMatchHistoryError);
    expect(publicHistory.MatchReplayTickError).toBe(MatchReplayTickError);
    expect(liveEnvelope.parsePlayerMatchEnvelope).toBe(parsePlayerMatchEnvelope);
    expect(liveEnvelope.parseSpectatorMatchEnvelope).toBe(parseSpectatorMatchEnvelope);
    expect(liveEnvelope.parseWebSocketApiErrorEnvelope).toBe(parseWebSocketApiErrorEnvelope);
    expect(publicContract.fetchPublicMatches).toBe(fetchPublicMatches);
    expect(publicContract.fetchPublicMatchDetail).toBe(fetchPublicMatchDetail);
    expect(publicContract.fetchPublicLeaderboard).toBe(fetchPublicLeaderboard);
    expect(publicContract.fetchPublicAgentProfile).toBe(fetchPublicAgentProfile);
    expect(publicContract.fetchPublicHumanProfile).toBe(fetchPublicHumanProfile);
    expect(publicContract.fetchCompletedMatches).toBe(fetchCompletedMatches);
    expect(publicContract.fetchPublicMatchHistory).toBe(fetchPublicMatchHistory);
    expect(publicContract.fetchMatchReplayTick).toBe(fetchMatchReplayTick);
    expect(publicContract.parsePlayerMatchEnvelope).toBe(parsePlayerMatchEnvelope);
    expect(publicContract.parseSpectatorMatchEnvelope).toBe(parseSpectatorMatchEnvelope);
    expect(publicContract.parseWebSocketApiErrorEnvelope).toBe(parseWebSocketApiErrorEnvelope);
    expect(publicContract.PublicMatchesError).toBe(PublicMatchesError);
    expect(publicContract.PublicMatchDetailError).toBe(PublicMatchDetailError);
    expect(publicContract.PublicLeaderboardError).toBe(PublicLeaderboardError);
    expect(publicContract.PublicAgentProfileError).toBe(PublicAgentProfileError);
    expect(publicContract.PublicHumanProfileError).toBe(PublicHumanProfileError);
    expect(publicContract.CompletedMatchesError).toBe(CompletedMatchesError);
    expect(publicContract.PublicMatchHistoryError).toBe(PublicMatchHistoryError);
    expect(publicContract.MatchReplayTickError).toBe(MatchReplayTickError);
  });
});


describe("authenticated api extraction seam", () => {
  it("keeps the extracted account session helpers available through both modules", () => {
    expect(accountSession.fetchOwnedApiKeys).toBe(fetchOwnedApiKeys);
    expect(accountSession.createOwnedApiKey).toBe(createOwnedApiKey);
    expect(accountSession.revokeOwnedApiKey).toBe(revokeOwnedApiKey);
    expect(accountSession.buildAuthenticatedHeaders).toBe(buildAuthenticatedHeaders);
    expect(accountSession.buildAuthenticatedJsonHeaders).toBe(buildAuthenticatedJsonHeaders);
    expect(accountSession.buildPlayerMatchWebSocketUrl).toBe(buildPlayerMatchWebSocketUrl);
    expect(accountSession.buildSpectatorMatchWebSocketUrl).toBe(buildSpectatorMatchWebSocketUrl);
    expect(accountSession.getPlayerWebSocketCloseMessage).toBe(getPlayerWebSocketCloseMessage);
    expect(accountSession.isApiErrorEnvelope).toBe(isApiErrorEnvelope);
    expect(accountSession.isRecord).toBe(isRecord);
    expect(accountSession.resolveApiBaseUrl).toBe(resolveApiBaseUrl);
    expect(accountSession.ApiKeyLifecycleError).toBe(ApiKeyLifecycleError);
  });

  it("keeps the extracted lobby lifecycle helpers available through both modules", () => {
    expect(lobbyLifecycle.createMatchLobby).toBe(createMatchLobby);
    expect(lobbyLifecycle.joinMatchLobby).toBe(joinMatchLobby);
    expect(lobbyLifecycle.startMatchLobby).toBe(startMatchLobby);
    expect(lobbyLifecycle.LobbyActionError).toBe(LobbyActionError);
  });

  it("keeps the extracted match write helpers available through both modules", () => {
    expect(matchWrites.submitMatchOrders).toBe(submitMatchOrders);
    expect(matchWrites.submitMatchMessage).toBe(submitMatchMessage);
    expect(matchWrites.submitGroupChatMessage).toBe(submitGroupChatMessage);
    expect(matchWrites.submitGroupChatCreate).toBe(submitGroupChatCreate);
    expect(matchWrites.submitTreatyAction).toBe(submitTreatyAction);
    expect(matchWrites.submitAllianceAction).toBe(submitAllianceAction);
    expect(matchWrites.CommandSubmissionError).toBe(CommandSubmissionError);
    expect(matchWrites.MessageSubmissionError).toBe(MessageSubmissionError);
    expect(matchWrites.GroupChatCreateError).toBe(GroupChatCreateError);
    expect(matchWrites.DiplomacySubmissionError).toBe(DiplomacySubmissionError);
  });

  it("keeps the extracted guided agent helpers available through both modules", () => {
    expect(guidedAgents.fetchOwnedAgentGuidedSession).toBe(fetchOwnedAgentGuidedSession);
    expect(guidedAgents.submitOwnedAgentGuidance).toBe(submitOwnedAgentGuidance);
    expect(guidedAgents.submitOwnedAgentOverride).toBe(submitOwnedAgentOverride);
    expect(guidedAgents.GuidedAgentControlsError).toBe(GuidedAgentControlsError);
  });
});
