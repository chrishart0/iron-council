from __future__ import annotations

from server import agent_registry_diplomacy
from server.agent_registry import (
    AdvancedMatchTick,
    AllianceTransitionError,
    GroupChatAccessError,
    InMemoryMatchRegistry,
    MatchAccessError,
    MatchJoinError,
    MatchRecord,
    TreatyTransitionError,
    build_seeded_agent_api_key,
    build_seeded_agent_profiles,
    build_seeded_match_records,
)
from server.auth import hash_api_key
from server.models.api import (
    AgentCommandEnvelopeRequest,
    AllianceActionRequest,
    AuthenticatedAgentContext,
    GroupChatCreateRequest,
    GroupChatMessageCreateRequest,
    MatchMessageCreateRequest,
    TreatyActionRequest,
    TreatyRecord,
)
from server.models.domain import MatchStatus
from server.models.orders import OrderEnvelope
from server.models.state import MatchState


def test_join_initializes_victory_countdown_for_new_sole_leader() -> None:
    registry = InMemoryMatchRegistry()
    registry.seed_match(
        MatchRecord(
            match_id="countdown-match",
            status=MatchStatus.ACTIVE,
            tick_interval_seconds=30,
            state=MatchState.model_validate(
                {
                    "tick": 12,
                    "cities": {
                        "alpha": {
                            "owner": "player-1",
                            "population": 5,
                            "resources": {"food": 1, "production": 1, "money": 1},
                            "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                            "garrison": 3,
                            "building_queue": [],
                        },
                        "beta": {
                            "owner": "player-2",
                            "population": 5,
                            "resources": {"food": 1, "production": 1, "money": 1},
                            "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                            "garrison": 3,
                            "building_queue": [],
                        },
                    },
                    "players": {
                        "player-1": {
                            "resources": {"food": 5, "production": 5, "money": 5},
                            "cities_owned": ["alpha"],
                            "alliance_id": None,
                            "is_eliminated": False,
                        },
                        "player-2": {
                            "resources": {"food": 5, "production": 5, "money": 5},
                            "cities_owned": ["beta"],
                            "alliance_id": None,
                            "is_eliminated": False,
                        },
                    },
                    "victory": {
                        "leading_alliance": None,
                        "cities_held": 1,
                        "threshold": 2,
                        "countdown_ticks_remaining": None,
                    },
                }
            ),
        )
    )

    created_alliance = registry.apply_alliance_action(
        match_id="countdown-match",
        action=AllianceActionRequest(
            match_id="countdown-match",
            action="create",
            name="Northern Pact",
        ),
        player_id="player-1",
    )
    joined_alliance = registry.apply_alliance_action(
        match_id="countdown-match",
        action=AllianceActionRequest(
            match_id="countdown-match",
            action="join",
            alliance_id=created_alliance.alliance_id if created_alliance is not None else None,
            name=None,
        ),
        player_id="player-2",
    )

    assert joined_alliance is not None
    match = registry.get_match("countdown-match")
    assert match is not None
    assert match.state.victory.model_dump(mode="json") == {
        "leading_alliance": joined_alliance.alliance_id,
        "cities_held": 2,
        "threshold": 2,
        "countdown_ticks_remaining": 2,
    }


def test_sync_victory_state_ignores_unowned_and_unknown_city_holders() -> None:
    state = MatchState.model_validate(
        {
            "tick": 8,
            "cities": {
                "alpha": {
                    "owner": None,
                    "population": 5,
                    "resources": {"food": 1, "production": 1, "money": 1},
                    "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                    "garrison": 3,
                    "building_queue": [],
                },
                "beta": {
                    "owner": "ghost-player",
                    "population": 5,
                    "resources": {"food": 1, "production": 1, "money": 1},
                    "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                    "garrison": 3,
                    "building_queue": [],
                },
            },
            "players": {
                "player-1": {
                    "resources": {"food": 5, "production": 5, "money": 5},
                    "cities_owned": [],
                    "alliance_id": None,
                    "is_eliminated": False,
                }
            },
            "victory": {
                "leading_alliance": "alliance-red",
                "cities_held": 2,
                "threshold": 2,
                "countdown_ticks_remaining": 1,
            },
        }
    )

    agent_registry_diplomacy.sync_victory_state(state)

    assert state.victory.model_dump(mode="json") == {
        "leading_alliance": None,
        "cities_held": 0,
        "threshold": 2,
        "countdown_ticks_remaining": None,
    }


def test_sync_victory_state_reinitializes_missing_countdown_for_same_leader() -> None:
    state = MatchState.model_validate(
        {
            "tick": 8,
            "cities": {
                "alpha": {
                    "owner": "player-1",
                    "population": 5,
                    "resources": {"food": 1, "production": 1, "money": 1},
                    "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                    "garrison": 3,
                    "building_queue": [],
                },
                "beta": {
                    "owner": "player-2",
                    "population": 5,
                    "resources": {"food": 1, "production": 1, "money": 1},
                    "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                    "garrison": 3,
                    "building_queue": [],
                },
            },
            "players": {
                "player-1": {
                    "resources": {"food": 5, "production": 5, "money": 5},
                    "cities_owned": ["alpha"],
                    "alliance_id": "alliance-red",
                    "is_eliminated": False,
                },
                "player-2": {
                    "resources": {"food": 5, "production": 5, "money": 5},
                    "cities_owned": ["beta"],
                    "alliance_id": "alliance-red",
                    "is_eliminated": False,
                },
            },
            "victory": {
                "leading_alliance": "alliance-red",
                "cities_held": 2,
                "threshold": 2,
                "countdown_ticks_remaining": None,
            },
        }
    )

    agent_registry_diplomacy.sync_victory_state(state)

    assert state.victory.model_dump(mode="json") == {
        "leading_alliance": "alliance-red",
        "cities_held": 2,
        "threshold": 2,
        "countdown_ticks_remaining": 2,
    }


def test_join_assigns_first_open_slot_and_is_idempotent_for_seeded_agent() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    first_join = registry.join_match(match_id="match-beta", agent_id="agent-player-2")
    repeat_join = registry.join_match(match_id="match-beta", agent_id="agent-player-2")
    second_join = registry.join_match(match_id="match-beta", agent_id="agent-player-3")

    assert first_join.model_dump(mode="json") == {
        "status": "accepted",
        "match_id": "match-beta",
        "agent_id": "agent-player-2",
        "player_id": "player-1",
    }
    assert repeat_join.model_dump(mode="json") == first_join.model_dump(mode="json")
    assert second_join.model_dump(mode="json") == {
        "status": "accepted",
        "match_id": "match-beta",
        "agent_id": "agent-player-3",
        "player_id": "player-2",
    }


def test_seeded_helpers_remain_available_from_agent_registry_compatibility_exports() -> None:
    from server import registry_seed_data

    assert build_seeded_agent_api_key is registry_seed_data.build_seeded_agent_api_key
    assert build_seeded_agent_profiles is registry_seed_data.build_seeded_agent_profiles
    assert build_seeded_match_records is registry_seed_data.build_seeded_match_records


def test_build_seeded_agent_api_key_preserves_public_seed_format() -> None:
    assert build_seeded_agent_api_key("agent-player-2") == "seed-api-key-for-agent-player-2"


def test_require_joined_player_id_returns_existing_mapping_after_join() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    join_response = registry.join_match(match_id="match-beta", agent_id="agent-player-2")

    assert (
        registry.require_joined_player_id(match_id="match-beta", agent_id="agent-player-2")
        == join_response.player_id
    )


def test_require_joined_player_id_rejects_authenticated_agent_without_join_mapping() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    try:
        registry.require_joined_player_id(match_id="match-beta", agent_id="agent-player-2")
    except MatchAccessError as exc:
        assert exc.code == "agent_not_joined"
        assert exc.message == (
            "Agent 'agent-player-2' has not joined match 'match-beta' as a player."
        )
    else:
        raise AssertionError("expected MatchAccessError for unjoined authenticated access")


def test_registry_list_helpers_return_empty_for_unknown_match() -> None:
    registry = InMemoryMatchRegistry()

    assert registry.list_order_submissions("match-missing") == []
    assert registry.list_treaties(match_id="match-missing") == []
    assert registry.list_alliances(match_id="match-missing") == []


def test_registry_message_and_briefing_views_preserve_visibility_and_since_tick_filters() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    registry.record_message(
        match_id="match-alpha",
        message=MatchMessageCreateRequest.model_validate(
            {
                "match_id": "match-alpha",
                "tick": 140,
                "channel": "world",
                "recipient_id": None,
                "content": "Old world intel.",
            }
        ),
        sender_id="player-1",
    )
    registry.record_message(
        match_id="match-alpha",
        message=MatchMessageCreateRequest.model_validate(
            {
                "match_id": "match-alpha",
                "tick": 142,
                "channel": "direct",
                "recipient_id": "player-2",
                "content": "Fresh direct ping.",
            }
        ),
        sender_id="player-1",
    )
    registry.record_message(
        match_id="match-alpha",
        message=MatchMessageCreateRequest.model_validate(
            {
                "match_id": "match-alpha",
                "tick": 142,
                "channel": "world",
                "recipient_id": None,
                "content": "Fresh world intel.",
            }
        ),
        sender_id="player-3",
    )
    created_group_chat = registry.create_group_chat(
        match_id="match-alpha",
        request=GroupChatCreateRequest(
            match_id="match-alpha",
            tick=140,
            name="Northern Channel",
            member_ids=["player-1"],
        ),
        creator_id="player-2",
    )
    registry.record_group_chat_message(
        match_id="match-alpha",
        group_chat_id=created_group_chat.group_chat_id,
        message=GroupChatMessageCreateRequest(
            match_id="match-alpha",
            tick=140,
            content="Old group note.",
        ),
        sender_id="player-1",
    )
    registry.record_group_chat_message(
        match_id="match-alpha",
        group_chat_id=created_group_chat.group_chat_id,
        message=GroupChatMessageCreateRequest(
            match_id="match-alpha",
            tick=142,
            content="Fresh group note.",
        ),
        sender_id="player-2",
    )

    assert [
        message.content
        for message in registry.list_visible_messages(match_id="match-alpha", player_id="player-2")
    ] == [
        "Old world intel.",
        "Fresh direct ping.",
        "Fresh world intel.",
    ]
    briefing = registry.list_briefing_messages(
        match_id="match-alpha",
        player_id="player-2",
        since_tick=142,
    )

    assert [message.content for message in briefing.direct] == ["Fresh direct ping."]
    assert [message.content for message in briefing.world] == ["Fresh world intel."]
    assert [message.content for message in briefing.group] == ["Fresh group note."]


def test_registry_group_chat_helpers_preserve_sorted_visibility_and_membership_errors() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    first_group_chat = registry.create_group_chat(
        match_id="match-alpha",
        request=GroupChatCreateRequest(
            match_id="match-alpha",
            tick=142,
            name="Northern Channel",
            member_ids=["player-1"],
        ),
        creator_id="player-2",
    )
    second_group_chat = registry.create_group_chat(
        match_id="match-alpha",
        request=GroupChatCreateRequest(
            match_id="match-alpha",
            tick=142,
            name="Western Channel",
            member_ids=["player-2"],
        ),
        creator_id="player-3",
    )

    assert [
        group_chat.group_chat_id
        for group_chat in registry.list_visible_group_chats(
            match_id="match-alpha", player_id="player-2"
        )
    ] == [
        first_group_chat.group_chat_id,
        second_group_chat.group_chat_id,
    ]

    try:
        registry.list_group_chat_messages(
            match_id="match-alpha",
            group_chat_id=second_group_chat.group_chat_id,
            player_id="player-1",
        )
    except GroupChatAccessError as exc:
        assert exc.code == "group_chat_not_visible"
        assert exc.message == "Group chat 'group-chat-2' is not visible to player 'player-1'."
    else:
        raise AssertionError("expected GroupChatAccessError for hidden group chat")


def test_registry_treaty_helpers_preserve_transition_side_effects_and_tick_filtering() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest(
            match_id="match-alpha",
            counterparty_id="player-3",
            action="propose",
            treaty_type="trade",
        ),
        player_id="player-2",
    )
    accepted_treaty = registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest(
            match_id="match-alpha",
            counterparty_id="player-2",
            action="accept",
            treaty_type="trade",
        ),
        player_id="player-3",
    )

    assert accepted_treaty.status == "active"
    assert [
        message.content
        for message in registry.list_visible_messages(match_id="match-alpha", player_id="player-1")
        if message.channel == "world"
    ] == ["Treaty signed: player-2 and player-3 entered a trade treaty."]
    assert [
        treaty.treaty_id
        for treaty in registry.list_treaties(match_id="match-alpha", since_tick=142)
    ] == [0]

    withdrawn_treaty = registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest(
            match_id="match-alpha",
            counterparty_id="player-3",
            action="withdraw",
            treaty_type="trade",
        ),
        player_id="player-2",
    )

    assert withdrawn_treaty.status == "withdrawn"
    assert [
        message.content
        for message in registry.list_visible_messages(match_id="match-alpha", player_id="player-1")
        if message.channel == "world"
    ] == [
        "Treaty signed: player-2 and player-3 entered a trade treaty.",
        "Treaty withdrawn: player-2 withdrew the trade treaty with player-3.",
    ]


def test_registry_alliance_helpers_preserve_leader_reassignment_and_empty_removal() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    remaining_alliance = registry.apply_alliance_action(
        match_id="match-alpha",
        action=AllianceActionRequest(
            match_id="match-alpha",
            action="leave",
            alliance_id=None,
            name=None,
        ),
        player_id="player-1",
    )

    assert remaining_alliance is not None
    assert remaining_alliance.model_dump(mode="json") == {
        "alliance_id": "alliance-red",
        "name": "alliance-red",
        "leader_id": "player-2",
        "formed_tick": 142,
        "members": [{"player_id": "player-2", "joined_tick": 142}],
    }

    removed_alliance = registry.apply_alliance_action(
        match_id="match-alpha",
        action=AllianceActionRequest(
            match_id="match-alpha",
            action="leave",
            alliance_id=None,
            name=None,
        ),
        player_id="player-2",
    )

    assert removed_alliance is None
    assert registry.list_alliances(match_id="match-alpha") == []


def test_registry_diplomacy_edges_preserve_input_errors_and_latest_tick_filtering() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    try:
        registry.apply_alliance_action(
            match_id="match-alpha",
            action=AllianceActionRequest.model_construct(
                match_id="match-alpha",
                action="create",
                alliance_id=None,
                name=None,
            ),
            player_id="player-3",
        )
    except AllianceTransitionError as exc:
        assert exc.code == "alliance_name_required"
        assert exc.message == "Alliance creation requires a non-empty name."
    else:
        raise AssertionError("expected alliance create without a name to fail")

    try:
        registry.apply_alliance_action(
            match_id="match-alpha",
            action=AllianceActionRequest.model_construct(
                match_id="match-alpha",
                action="join",
                alliance_id=None,
                name=None,
            ),
            player_id="player-3",
        )
    except AllianceTransitionError as exc:
        assert exc.code == "alliance_id_required"
        assert exc.message == "Alliance join requires an alliance_id."
    else:
        raise AssertionError("expected alliance join without an id to fail")

    try:
        registry.apply_treaty_action(
            match_id="match-alpha",
            action=TreatyActionRequest(
                match_id="match-alpha",
                counterparty_id="player-3",
                action="accept",
                treaty_type="trade",
            ),
            player_id="player-2",
        )
    except TreatyTransitionError as exc:
        assert exc.code == "unsupported_treaty_transition"
        assert exc.message == "Cannot accept treaty 'trade' for players 'player-2' and 'player-3'."
    else:
        raise AssertionError("expected treaty accept without a proposal to fail")

    try:
        registry.apply_treaty_action(
            match_id="match-alpha",
            action=TreatyActionRequest(
                match_id="match-alpha",
                counterparty_id="player-3",
                action="withdraw",
                treaty_type="trade",
            ),
            player_id="player-2",
        )
    except TreatyTransitionError as exc:
        assert exc.code == "treaty_not_found"
        assert exc.message == (
            "No treaty exists for players 'player-2' and 'player-3' with type 'trade'."
        )
    else:
        raise AssertionError("expected treaty withdraw without an existing treaty to fail")

    registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest(
            match_id="match-alpha",
            counterparty_id="player-3",
            action="propose",
            treaty_type="trade",
        ),
        player_id="player-2",
    )
    registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest(
            match_id="match-alpha",
            counterparty_id="player-2",
            action="accept",
            treaty_type="trade",
        ),
        player_id="player-3",
    )

    match = registry.get_match("match-alpha")
    assert match is not None
    match.state.tick = 143

    withdrawn_treaty = registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest(
            match_id="match-alpha",
            counterparty_id="player-3",
            action="withdraw",
            treaty_type="trade",
        ),
        player_id="player-2",
    )

    assert withdrawn_treaty.status == "withdrawn"
    assert [
        treaty.model_dump(mode="json") for treaty in registry.list_treaties(match_id="match-alpha")
    ] == [
        {
            "treaty_id": 0,
            "player_a_id": "player-2",
            "player_b_id": "player-3",
            "treaty_type": "trade",
            "status": "withdrawn",
            "proposed_by": "player-2",
            "proposed_tick": 142,
            "signed_tick": 142,
            "withdrawn_by": "player-2",
            "withdrawn_tick": 143,
        }
    ]
    assert [
        treaty.treaty_id
        for treaty in registry.list_treaties(match_id="match-alpha", since_tick=143)
    ] == [0]
    assert registry.list_treaties(match_id="match-alpha", since_tick=144) == []

    try:
        registry.apply_treaty_action(
            match_id="match-alpha",
            action=TreatyActionRequest(
                match_id="match-alpha",
                counterparty_id="player-2",
                action="accept",
                treaty_type="trade",
            ),
            player_id="player-3",
        )
    except TreatyTransitionError as exc:
        assert exc.code == "unsupported_treaty_transition"
        assert exc.message == "Cannot accept treaty 'trade' for players 'player-2' and 'player-3'."
    else:
        raise AssertionError("expected treaty accept after withdrawal to fail")


def test_registry_record_message_rejects_invalid_recipients_without_mutating_history() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    before_state = registry.snapshot_match("match-alpha")

    try:
        registry.record_message(
            match_id="match-alpha",
            message=MatchMessageCreateRequest.model_validate(
                {
                    "match_id": "match-alpha",
                    "tick": 142,
                    "channel": "world",
                    "recipient_id": "player-2",
                    "content": "This should fail.",
                }
            ),
            sender_id="player-1",
        )
    except MatchAccessError as exc:
        assert exc.code == "unsupported_recipient"
        assert exc.message == "World messages do not support recipient_id."
    else:
        raise AssertionError("expected world message recipient validation to fail")

    try:
        registry.record_message(
            match_id="match-alpha",
            message=MatchMessageCreateRequest.model_validate(
                {
                    "match_id": "match-alpha",
                    "tick": 142,
                    "channel": "direct",
                    "recipient_id": "player-missing",
                    "content": "This should also fail.",
                }
            ),
            sender_id="player-1",
        )
    except MatchAccessError as exc:
        assert exc.code == "unsupported_recipient"
        assert exc.message == (
            "Direct messages require a recipient_id for a player in match 'match-alpha'."
        )
    else:
        raise AssertionError("expected direct message recipient validation to fail")

    after_state = registry.snapshot_match("match-alpha")
    assert after_state == before_state


def test_registry_briefing_and_group_message_views_hide_non_member_chat_activity() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    visible_group_chat = registry.create_group_chat(
        match_id="match-alpha",
        request=GroupChatCreateRequest(
            match_id="match-alpha",
            tick=142,
            name="Visible Channel",
            member_ids=["player-3"],
        ),
        creator_id="player-2",
    )
    hidden_group_chat = registry.create_group_chat(
        match_id="match-alpha",
        request=GroupChatCreateRequest(
            match_id="match-alpha",
            tick=142,
            name="Hidden Channel",
            member_ids=["player-4"],
        ),
        creator_id="player-1",
    )
    registry.record_group_chat_message(
        match_id="match-alpha",
        group_chat_id=visible_group_chat.group_chat_id,
        message=GroupChatMessageCreateRequest(
            match_id="match-alpha",
            tick=142,
            content="Visible note.",
        ),
        sender_id="player-2",
    )
    registry.record_group_chat_message(
        match_id="match-alpha",
        group_chat_id=hidden_group_chat.group_chat_id,
        message=GroupChatMessageCreateRequest(
            match_id="match-alpha",
            tick=142,
            content="Hidden note.",
        ),
        sender_id="player-1",
    )
    registry.record_message(
        match_id="match-alpha",
        message=MatchMessageCreateRequest.model_validate(
            {
                "match_id": "match-alpha",
                "tick": 142,
                "channel": "direct",
                "recipient_id": "player-2",
                "content": "Private ping.",
            }
        ),
        sender_id="player-1",
    )

    briefing = registry.list_briefing_messages(
        match_id="match-alpha",
        player_id="player-3",
        since_tick=142,
    )

    assert [message.content for message in briefing.direct] == []
    assert [message.content for message in briefing.world] == []
    assert [
        (message.group_chat_id, message.content)
        for message in registry.list_visible_group_chat_messages(
            match_id="match-alpha",
            player_id="player-3",
            since_tick=142,
        )
    ] == [(visible_group_chat.group_chat_id, "Visible note.")]
    assert [(message.group_chat_id, message.content) for message in briefing.group] == [
        (visible_group_chat.group_chat_id, "Visible note.")
    ]

    try:
        registry.record_group_chat_message(
            match_id="match-alpha",
            group_chat_id=hidden_group_chat.group_chat_id,
            message=GroupChatMessageCreateRequest(
                match_id="match-alpha",
                tick=142,
                content="Intrusion attempt.",
            ),
            sender_id="player-3",
        )
    except GroupChatAccessError as exc:
        assert exc.code == "group_chat_not_visible"
        assert exc.message == (
            f"Group chat '{hidden_group_chat.group_chat_id}' is not visible to player 'player-3'."
        )
    else:
        raise AssertionError("expected hidden group chat send to fail for non-member")


def test_get_agent_profile_returns_stable_seeded_placeholder_shape() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    profile = registry.get_agent_profile("agent-player-2")

    assert profile is not None
    assert profile.model_dump(mode="json") == {
        "agent_id": "agent-player-2",
        "display_name": "Morgana",
        "is_seeded": True,
        "rating": {"elo": 1190, "provisional": True},
        "history": {"matches_played": 0, "wins": 0, "losses": 0, "draws": 0},
        "treaty_reputation": {
            "summary": {
                "signed": 0,
                "active": 0,
                "honored": 0,
                "withdrawn": 0,
                "broken_by_self": 0,
                "broken_by_counterparty": 0,
            },
            "history": [],
        },
    }


def test_resolve_authenticated_agent_returns_seeded_identity_without_raw_key_material() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    authenticated_agent = registry.resolve_authenticated_agent(
        build_seeded_agent_api_key("agent-player-2")
    )

    assert authenticated_agent is not None
    assert authenticated_agent.model_dump(mode="json") == {
        "agent_id": "agent-player-2",
        "display_name": "Morgana",
        "is_seeded": True,
    }


def test_resolve_authenticated_agent_rejects_unknown_and_inactive_keys() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)
    registry.deactivate_agent_api_key("agent-player-3")

    assert registry.resolve_authenticated_agent("missing-key") is None
    assert (
        registry.resolve_authenticated_agent(build_seeded_agent_api_key("agent-player-3")) is None
    )


def test_deactivate_agent_api_key_removes_all_seeded_key_hashes_for_agent_only() -> None:
    registry = InMemoryMatchRegistry()
    primary_key = build_seeded_agent_api_key("agent-player-2")
    backup_key = "seed-api-key-for-agent-player-2-backup"
    other_key = build_seeded_agent_api_key("agent-player-3")
    primary_hash = hash_api_key(primary_key)
    backup_hash = hash_api_key(backup_key)
    other_hash = hash_api_key(other_key)

    registry.seed_authenticated_agent_key(
        AuthenticatedAgentContext(
            agent_id="agent-player-2",
            display_name="Morgana",
            is_seeded=True,
        ),
        key_hash=primary_hash,
    )
    registry.seed_authenticated_agent_key(
        AuthenticatedAgentContext(
            agent_id="agent-player-2",
            display_name="Morgana",
            is_seeded=True,
        ),
        key_hash=backup_hash,
    )
    registry.seed_authenticated_agent_key(
        AuthenticatedAgentContext(
            agent_id="agent-player-3",
            display_name="Merlin",
            is_seeded=True,
        ),
        key_hash=other_hash,
    )

    registry.deactivate_agent_api_key("agent-player-2")

    assert registry.resolve_authenticated_agent(primary_key) is None
    assert registry.resolve_authenticated_agent(backup_key) is None
    assert registry.resolve_authenticated_agent(other_key) is not None
    assert registry._authenticated_agents_by_key_hash == {  # noqa: SLF001
        other_hash: AuthenticatedAgentContext(
            agent_id="agent-player-3",
            display_name="Merlin",
            is_seeded=True,
        )
    }


def test_join_rejects_non_joinable_and_full_matches_without_side_effects() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    non_joinable_match = registry.get_match("match-alpha")
    assert non_joinable_match is not None
    baseline_non_joinable_assignments = dict(non_joinable_match.joined_agents)

    try:
        registry.join_match(match_id="match-alpha", agent_id="agent-player-new")
    except MatchJoinError as exc:
        error = exc
    else:  # pragma: no cover
        raise AssertionError("expected non-joinable match to reject join")

    assert error.code == "match_not_joinable"
    assert error.message == "Match 'match-alpha' does not support agent joins."
    assert non_joinable_match.joined_agents == baseline_non_joinable_assignments

    registry.join_match(match_id="match-beta", agent_id="agent-player-1")
    registry.join_match(match_id="match-beta", agent_id="agent-player-2")
    registry.join_match(match_id="match-beta", agent_id="agent-player-3")
    registry.join_match(match_id="match-beta", agent_id="agent-player-4")
    registry.join_match(match_id="match-beta", agent_id="agent-player-5")

    full_match = registry.get_match("match-beta")
    assert full_match is not None
    baseline_full_assignments = dict(full_match.joined_agents)

    try:
        registry.join_match(match_id="match-beta", agent_id="agent-overflow")
    except MatchJoinError as exc:
        error = exc
    else:  # pragma: no cover
        raise AssertionError("expected full match to reject join")

    assert error.code == "no_open_slots"
    assert error.message == "Match 'match-beta' has no open join slots."
    assert full_match.joined_agents == baseline_full_assignments


def test_reset_clears_seeded_matches_and_profiles() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    registry.reset()

    assert registry.list_matches() == []
    assert registry.get_match("match-alpha") is None
    assert registry.get_agent_profile("agent-player-2") is None


def test_replace_player_submissions_replaces_same_player_same_tick_orders() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-2",
                "tick": 142,
                "orders": {
                    "movements": [{"army_id": "army-b", "destination": "york"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-2",
                "tick": 142,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "manchester", "troops": 1}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-3",
                "tick": 142,
                "orders": {
                    "movements": [{"army_id": "army-c", "destination": "oxford"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )

    submission_index, superseded_submission_count = registry.replace_player_submissions(
        match_id="match-alpha",
        player_id="player-2",
        tick=142,
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-2",
                "tick": 142,
                "orders": {
                    "movements": [{"army_id": "army-b", "destination": "london"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )

    assert submission_index == 1
    assert superseded_submission_count == 2
    assert registry.list_order_submissions("match-alpha") == [
        {
            "match_id": "match-alpha",
            "player_id": "player-3",
            "tick": 142,
            "orders": {
                "movements": [{"army_id": "army-c", "destination": "oxford"}],
                "recruitment": [],
                "upgrades": [],
                "transfers": [],
            },
        },
        {
            "match_id": "match-alpha",
            "player_id": "player-2",
            "tick": 142,
            "orders": {
                "movements": [{"army_id": "army-b", "destination": "london"}],
                "recruitment": [],
                "upgrades": [],
                "transfers": [],
            },
        },
    ]


def test_replace_player_submissions_keeps_other_ticks_and_players_queued() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-2",
                "tick": 143,
                "orders": {
                    "movements": [{"army_id": "army-b", "destination": "york"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 142,
                "orders": {
                    "movements": [{"army_id": "army-a", "destination": "birmingham"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )

    submission_index, superseded_submission_count = registry.replace_player_submissions(
        match_id="match-alpha",
        player_id="player-2",
        tick=142,
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-2",
                "tick": 142,
                "orders": {
                    "movements": [{"army_id": "army-b", "destination": "london"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )

    assert submission_index == 2
    assert superseded_submission_count == 0
    assert registry.list_order_submissions("match-alpha") == [
        {
            "match_id": "match-alpha",
            "player_id": "player-2",
            "tick": 143,
            "orders": {
                "movements": [{"army_id": "army-b", "destination": "york"}],
                "recruitment": [],
                "upgrades": [],
                "transfers": [],
            },
        },
        {
            "match_id": "match-alpha",
            "player_id": "player-1",
            "tick": 142,
            "orders": {
                "movements": [{"army_id": "army-a", "destination": "birmingham"}],
                "recruitment": [],
                "upgrades": [],
                "transfers": [],
            },
        },
        {
            "match_id": "match-alpha",
            "player_id": "player-2",
            "tick": 142,
            "orders": {
                "movements": [{"army_id": "army-b", "destination": "london"}],
                "recruitment": [],
                "upgrades": [],
                "transfers": [],
            },
        },
    ]


def test_advance_match_tick_resolves_current_orders_and_keeps_future_submissions_queued() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 142,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "london", "troops": 5}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 143,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "london", "troops": 1}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )

    registry.advance_match_tick("match-alpha")

    match = registry.get_match("match-alpha")
    assert match is not None
    assert match.state.tick == 143
    assert next(army for army in match.state.armies if army.id == "army-b").troops == 25
    assert [submission.model_dump(mode="json") for submission in match.order_submissions] == [
        {
            "match_id": "match-alpha",
            "player_id": "player-1",
            "tick": 143,
            "orders": {
                "movements": [],
                "recruitment": [{"city": "london", "troops": 1}],
                "upgrades": [],
                "transfers": [],
            },
        }
    ]


def test_advance_match_tick_combines_same_player_submissions_before_validation() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 142,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "london", "troops": 4}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 142,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "london", "troops": 4}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )

    registry.advance_match_tick("match-alpha")

    match = registry.get_match("match-alpha")
    assert match is not None
    assert match.state.tick == 143
    assert match.state.players["player-1"].resources.model_dump(mode="json") == {
        "food": 83,
        "production": 47,
        "money": 213,
    }
    assert [
        (army.id, army.location, army.owner, army.troops)
        for army in match.state.armies
        if army.owner == "player-1" and army.location == "london"
    ] == [("army-b", "london", "player-1", 28)]
    assert match.order_submissions == []


def test_advance_match_tick_returns_resolved_tick_contract_for_persistence() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 142,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "london", "troops": 5}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )
    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 143,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "london", "troops": 1}],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )

    advanced_tick = registry.advance_match_tick("match-alpha")

    assert isinstance(advanced_tick, AdvancedMatchTick)
    assert advanced_tick.match_id == "match-alpha"
    assert advanced_tick.resolved_tick == 143
    assert advanced_tick.next_state.tick == 143
    assert advanced_tick.accepted_orders.model_dump(mode="json") == {
        "movements": [],
        "recruitment": [{"city": "london", "troops": 5}],
        "upgrades": [],
        "transfers": [],
    }
    assert [event.model_dump(mode="json") for event in advanced_tick.events] == [
        {"phase": "resource", "event": "phase.resource.completed"},
        {"phase": "build", "event": "phase.build.completed"},
        {"phase": "movement", "event": "phase.movement.completed"},
        {"phase": "combat", "event": "phase.combat.completed"},
        {"phase": "siege", "event": "phase.siege.completed"},
        {"phase": "attrition", "event": "phase.attrition.completed"},
        {"phase": "diplomacy", "event": "phase.diplomacy.completed"},
        {"phase": "victory", "event": "phase.victory.completed"},
    ]

    match = registry.get_match("match-alpha")
    assert match is not None
    assert [submission.model_dump(mode="json") for submission in match.order_submissions] == [
        {
            "match_id": "match-alpha",
            "player_id": "player-1",
            "tick": 143,
            "orders": {
                "movements": [],
                "recruitment": [{"city": "london", "troops": 1}],
                "upgrades": [],
                "transfers": [],
            },
        }
    ]


def test_apply_command_envelope_accepts_orders_and_messages_without_contract_drift() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    accepted = registry.apply_command_envelope(
        match_id="match-alpha",
        player_id="player-2",
        command=AgentCommandEnvelopeRequest.model_validate(
            {
                "match_id": "match-alpha",
                "tick": 142,
                "orders": {
                    "movements": [],
                    "recruitment": [{"city": "manchester", "troops": 3}],
                    "upgrades": [],
                    "transfers": [],
                },
                "messages": [
                    {
                        "channel": "direct",
                        "recipient_id": "player-3",
                        "content": "Reinforcements en route.",
                    }
                ],
            }
        ),
    )

    assert accepted.model_dump(mode="json") == {
        "status": "accepted",
        "match_id": "match-alpha",
        "player_id": "player-2",
        "tick": 142,
        "orders": {
            "status": "accepted",
            "match_id": "match-alpha",
            "player_id": "player-2",
            "tick": 142,
            "submission_index": 0,
        },
        "messages": [
            {
                "status": "accepted",
                "match_id": "match-alpha",
                "message_id": 0,
                "channel": "direct",
                "sender_id": "player-2",
                "recipient_id": "player-3",
                "tick": 142,
                "content": "Reinforcements en route.",
            }
        ],
        "treaties": [],
        "alliance": None,
    }
    assert registry.list_order_submissions("match-alpha") == [
        {
            "match_id": "match-alpha",
            "player_id": "player-2",
            "tick": 142,
            "orders": {
                "movements": [],
                "recruitment": [{"city": "manchester", "troops": 3}],
                "upgrades": [],
                "transfers": [],
            },
        }
    ]
    assert [
        message.model_dump(mode="json")
        for message in registry.list_visible_messages(match_id="match-alpha", player_id="player-3")
        if message.channel == "direct"
    ] == [
        {
            "message_id": 0,
            "channel": "direct",
            "sender_id": "player-2",
            "recipient_id": "player-3",
            "tick": 142,
            "content": "Reinforcements en route.",
        }
    ]


def test_apply_command_envelope_routes_treaty_acceptance_world_side_effects() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest(
            match_id="match-alpha",
            counterparty_id="player-3",
            action="propose",
            treaty_type="trade",
        ),
        player_id="player-2",
    )

    accepted = registry.apply_command_envelope(
        match_id="match-alpha",
        player_id="player-3",
        command=AgentCommandEnvelopeRequest.model_validate(
            {
                "match_id": "match-alpha",
                "tick": 142,
                "treaties": [
                    {
                        "counterparty_id": "player-2",
                        "action": "accept",
                        "treaty_type": "trade",
                    }
                ],
            }
        ),
    )

    assert accepted.model_dump(mode="json") == {
        "status": "accepted",
        "match_id": "match-alpha",
        "player_id": "player-3",
        "tick": 142,
        "orders": None,
        "messages": [],
        "treaties": [
            {
                "status": "accepted",
                "match_id": "match-alpha",
                "treaty": {
                    "treaty_id": 0,
                    "player_a_id": "player-2",
                    "player_b_id": "player-3",
                    "treaty_type": "trade",
                    "status": "active",
                    "proposed_by": "player-2",
                    "proposed_tick": 142,
                    "signed_tick": 142,
                    "withdrawn_by": None,
                    "withdrawn_tick": None,
                },
            }
        ],
        "alliance": None,
    }
    assert [
        message.content
        for message in registry.list_visible_messages(match_id="match-alpha", player_id="player-1")
        if message.channel == "world"
    ] == ["Treaty signed: player-2 and player-3 entered a trade treaty."]


def test_treaty_record_accepts_broken_statuses() -> None:
    broken_by_a = TreatyRecord(
        treaty_id=7,
        player_a_id="player-1",
        player_b_id="player-2",
        treaty_type="non_aggression",
        status="broken_by_a",
        proposed_by="player-1",
        proposed_tick=10,
        signed_tick=11,
        withdrawn_by="player-1",
        withdrawn_tick=12,
    )
    broken_by_b = broken_by_a.model_copy(
        update={"status": "broken_by_b", "withdrawn_by": "player-2"}
    )

    assert broken_by_a.status == "broken_by_a"
    assert broken_by_b.status == "broken_by_b"


def test_advance_match_tick_breaks_active_treaties_when_attacking_partner_in_neutral_city() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    match = registry.get_match("match-alpha")
    assert match is not None
    match.state.cities["birmingham"].owner = None
    match.state.players["player-2"].cities_owned = ["manchester"]
    match.state.players["player-3"].cities_owned = []
    army_a = next(army for army in match.state.armies if army.id == "army-a")
    army_a.location = "birmingham"
    army_a.destination = None
    army_a.path = None
    army_a.ticks_remaining = 0

    registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest(
            match_id="match-alpha",
            counterparty_id="player-1",
            action="propose",
            treaty_type="trade",
        ),
        player_id="player-2",
    )
    registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest(
            match_id="match-alpha",
            counterparty_id="player-2",
            action="accept",
            treaty_type="trade",
        ),
        player_id="player-1",
    )
    registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest(
            match_id="match-alpha",
            counterparty_id="player-1",
            action="propose",
            treaty_type="non_aggression",
        ),
        player_id="player-2",
    )
    registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest(
            match_id="match-alpha",
            counterparty_id="player-2",
            action="accept",
            treaty_type="non_aggression",
        ),
        player_id="player-1",
    )
    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-1",
                "tick": 142,
                "orders": {
                    "movements": [{"army_id": "army-b", "destination": "birmingham"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )

    advanced_tick = registry.advance_match_tick("match-alpha")

    treaties = registry.list_treaties(match_id="match-alpha")
    assert advanced_tick.accepted_orders.model_dump(mode="json") == {
        "movements": [{"army_id": "army-b", "destination": "birmingham"}],
        "recruitment": [],
        "upgrades": [],
        "transfers": [],
    }
    assert treaties == [
        TreatyRecord(
            treaty_id=1,
            player_a_id="player-1",
            player_b_id="player-2",
            treaty_type="non_aggression",
            status="broken_by_a",
            proposed_by="player-2",
            proposed_tick=142,
            signed_tick=142,
            withdrawn_by="player-1",
            withdrawn_tick=142,
        ),
        TreatyRecord(
            treaty_id=0,
            player_a_id="player-1",
            player_b_id="player-2",
            treaty_type="trade",
            status="broken_by_a",
            proposed_by="player-2",
            proposed_tick=142,
            signed_tick=142,
            withdrawn_by="player-1",
            withdrawn_tick=142,
        ),
    ]
    assert [
        message.content
        for message in registry.list_visible_messages(match_id="match-alpha", player_id="player-3")
        if message.channel == "world"
    ] == [
        "Treaty signed: player-1 and player-2 entered a trade treaty.",
        "Treaty signed: player-1 and player-2 entered a non_aggression treaty.",
        "Treaty broken: player-1 attacked player-2 and broke their trade treaty.",
        "Treaty broken: player-1 attacked player-2 and broke their non_aggression treaty.",
    ]


def test_advance_match_tick_marks_broken_by_b_when_player_b_attacks_partner_city() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    match = registry.get_match("match-alpha")
    assert match is not None
    match.state.cities["manchester"].owner = "player-1"
    match.state.players["player-1"].cities_owned = ["manchester"]
    match.state.players["player-2"].cities_owned = []
    army_a = next(army for army in match.state.armies if army.id == "army-a")
    army_a.location = "birmingham"
    army_a.destination = None
    army_a.path = None
    army_a.ticks_remaining = 0

    registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest(
            match_id="match-alpha",
            counterparty_id="player-1",
            action="propose",
            treaty_type="trade",
        ),
        player_id="player-2",
    )
    registry.apply_treaty_action(
        match_id="match-alpha",
        action=TreatyActionRequest(
            match_id="match-alpha",
            counterparty_id="player-2",
            action="accept",
            treaty_type="trade",
        ),
        player_id="player-1",
    )
    registry.record_submission(
        match_id="match-alpha",
        envelope=OrderEnvelope.model_validate(
            {
                "match_id": "match-alpha",
                "player_id": "player-2",
                "tick": 142,
                "orders": {
                    "movements": [{"army_id": "army-a", "destination": "manchester"}],
                    "recruitment": [],
                    "upgrades": [],
                    "transfers": [],
                },
            }
        ),
    )

    registry.advance_match_tick("match-alpha")

    assert registry.list_treaties(match_id="match-alpha") == [
        TreatyRecord(
            treaty_id=0,
            player_a_id="player-1",
            player_b_id="player-2",
            treaty_type="trade",
            status="broken_by_b",
            proposed_by="player-2",
            proposed_tick=142,
            signed_tick=142,
            withdrawn_by="player-2",
            withdrawn_tick=142,
        )
    ]


def test_apply_command_envelope_uses_scratch_registry_to_prevent_partial_mutation() -> None:
    registry = InMemoryMatchRegistry()
    for record in build_seeded_match_records():
        registry.seed_match(record)

    before_state = registry.snapshot_match("match-alpha")

    try:
        registry.apply_command_envelope(
            match_id="match-alpha",
            player_id="player-2",
            command=AgentCommandEnvelopeRequest.model_validate(
                {
                    "match_id": "match-alpha",
                    "tick": 142,
                    "orders": {
                        "movements": [],
                        "recruitment": [{"city": "manchester", "troops": 3}],
                        "upgrades": [],
                        "transfers": [],
                    },
                    "messages": [
                        {
                            "channel": "world",
                            "content": "This should not persist.",
                        }
                    ],
                    "treaties": [
                        {
                            "counterparty_id": "player-2",
                            "action": "propose",
                            "treaty_type": "trade",
                        }
                    ],
                }
            ),
        )
    except MatchAccessError as exc:
        assert exc.code == "self_targeted_treaty"
        assert exc.message == "Treaty actions require two different players."
    else:  # pragma: no cover
        raise AssertionError("expected command envelope validation to reject self-targeted treaty")

    after_state = registry.snapshot_match("match-alpha")
    assert registry.list_order_submissions("match-alpha") == []
    assert after_state == before_state
