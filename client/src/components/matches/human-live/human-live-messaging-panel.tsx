import type { GroupChatRecord } from "../../../lib/types";
import type {
  AsyncSubmissionFeedback,
  GroupChatCreateDraftState,
  LiveMessagingChannel,
  MessageDraftState
} from "./human-match-live-types";

type HumanLiveMessagingPanelProps = {
  visiblePlayerIds: string[];
  visibleGroupChats: GroupChatRecord[];
  groupChatCreateDraft: GroupChatCreateDraftState;
  groupChatCreateFeedback: AsyncSubmissionFeedback;
  messageDraft: MessageDraftState;
  messageSubmissionFeedback: AsyncSubmissionFeedback;
  canSubmitGroupChatCreate: boolean;
  canSubmitMessage: boolean;
  updateGroupChatCreateDraft: (updates: Partial<GroupChatCreateDraftState>) => void;
  updateMessageDraft: (updates: Partial<MessageDraftState>) => void;
  submitGroupChatCreateDraft: () => Promise<void>;
  submitMessageDraft: () => Promise<void>;
};

export function HumanLiveMessagingPanel({
  visiblePlayerIds,
  visibleGroupChats,
  groupChatCreateDraft,
  groupChatCreateFeedback,
  messageDraft,
  messageSubmissionFeedback,
  canSubmitGroupChatCreate,
  canSubmitMessage,
  updateGroupChatCreateDraft,
  updateMessageDraft,
  submitGroupChatCreateDraft,
  submitMessageDraft
}: HumanLiveMessagingPanelProps) {
  return (
    <section className="panel panel-section">
      <h2>Live messaging</h2>
      <p>Submit world, direct, or group messages for the current websocket tick. The live timeline stays read-only.</p>

      <section aria-label="Create group chat">
        <h3>Create group chat</h3>
        <p>Use the current websocket snapshot to choose visible players, then wait for the next snapshot to show the chat in the live list.</p>

        {groupChatCreateFeedback.status === "success" ? (
          <div role="status">
            <p>{groupChatCreateFeedback.message}</p>
            {groupChatCreateFeedback.details?.map((detail) => <p key={detail}>{detail}</p>)}
          </div>
        ) : null}

        {groupChatCreateFeedback.status === "error" ? (
          <div role="alert">
            <p>{groupChatCreateFeedback.message}</p>
            <p>{`Error code: ${groupChatCreateFeedback.code}`}</p>
            <p>{`HTTP status: ${groupChatCreateFeedback.statusCode}`}</p>
          </div>
        ) : null}

        <label>
          Group chat name
          <input
            type="text"
            value={groupChatCreateDraft.name}
            onChange={(event) => updateGroupChatCreateDraft({ name: event.target.value })}
          />
        </label>

        {visiblePlayerIds.length === 0 ? (
          <p>No other visible players can be invited from the current snapshot.</p>
        ) : (
          <fieldset>
            <legend>Invite players</legend>
            {visiblePlayerIds.map((playerId) => {
              const isChecked = groupChatCreateDraft.selectedInviteeIds.includes(playerId);

              return (
                <label key={playerId}>
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={(event) => {
                      const nextSelectedInviteeIds = event.target.checked
                        ? [...groupChatCreateDraft.selectedInviteeIds, playerId]
                        : groupChatCreateDraft.selectedInviteeIds.filter(
                            (selectedPlayerId) => selectedPlayerId !== playerId
                          );

                      updateGroupChatCreateDraft({ selectedInviteeIds: nextSelectedInviteeIds });
                    }}
                  />
                  {playerId}
                </label>
              );
            })}
          </fieldset>
        )}

        <button
          className="button-link"
          type="button"
          onClick={() => void submitGroupChatCreateDraft()}
          disabled={!canSubmitGroupChatCreate}
        >
          {groupChatCreateFeedback.status === "submitting" ? "Submitting…" : "Create group chat"}
        </button>
      </section>

      {messageSubmissionFeedback.status === "success" ? <p role="status">{messageSubmissionFeedback.message}</p> : null}

      {messageSubmissionFeedback.status === "error" ? (
        <div role="alert">
          <p>{messageSubmissionFeedback.message}</p>
          <p>{`Error code: ${messageSubmissionFeedback.code}`}</p>
          <p>{`HTTP status: ${messageSubmissionFeedback.statusCode}`}</p>
        </div>
      ) : null}

      <label>
        Channel
        <select
          value={messageDraft.channel}
          onChange={(event) => updateMessageDraft({ channel: event.target.value as LiveMessagingChannel })}
        >
          <option value="world">world</option>
          <option value="direct">direct</option>
          <option value="group">group</option>
        </select>
      </label>

      {messageDraft.channel === "direct" ? (
        <label>
          Direct target
          <select
            value={messageDraft.directRecipientId}
            onChange={(event) => updateMessageDraft({ directRecipientId: event.target.value })}
          >
            {visiblePlayerIds.length === 0 ? <option value="">No visible players</option> : null}
            {visiblePlayerIds.map((playerId) => (
              <option key={playerId} value={playerId}>
                {playerId}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {messageDraft.channel === "group" ? (
        <label>
          Group chat
          <select value={messageDraft.groupChatId} onChange={(event) => updateMessageDraft({ groupChatId: event.target.value })}>
            {visibleGroupChats.length === 0 ? <option value="">No visible group chats</option> : null}
            {visibleGroupChats.map((groupChat) => (
              <option key={groupChat.group_chat_id} value={groupChat.group_chat_id}>
                {groupChat.name}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      <label>
        Message content
        <textarea value={messageDraft.content} onChange={(event) => updateMessageDraft({ content: event.target.value })} />
      </label>

      <button className="button-link" type="button" onClick={() => void submitMessageDraft()} disabled={!canSubmitMessage}>
        {messageSubmissionFeedback.status === "submitting" ? "Submitting…" : "Submit message"}
      </button>
    </section>
  );
}
