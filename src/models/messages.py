from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from src.utils.settings import MessageType

@dataclass
class NetworkMessage:
    type: MessageType

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['type'] = self.type.value
        return d

@dataclass
class ConnectAckMessage(NetworkMessage):
    player_id: int
    type: MessageType = field(default=MessageType.CONNECT_ACK, init=False)

@dataclass
class GameStateUpdateMessage(NetworkMessage):
    state: Dict[str, Any]
    type: MessageType = field(default=MessageType.GAME_STATE_UPDATE, init=False)

@dataclass
class StartGameMessage(NetworkMessage):
    type: MessageType = field(default=MessageType.START_GAME, init=False)

@dataclass
class PlayerRoleMessage(NetworkMessage):
    player_id: int
    role: str
    type: MessageType = field(default=MessageType.PLAYER_ROLE, init=False)

@dataclass
class RequestTeamSelectionMessage(NetworkMessage):
    leader_id: int
    mission_size: int
    available_players_ids: List[int]
    type: MessageType = field(default=MessageType.REQUEST_TEAM_SELECTION, init=False)

@dataclass
class TeamProposedMessage(NetworkMessage):
    player_id: int
    team: List[int]
    type: MessageType = field(default=MessageType.TEAM_PROPOSED, init=False)

@dataclass
class RequestVoteMessage(NetworkMessage):
    player_id: int
    team: List[int]
    type: MessageType = field(default=MessageType.REQUEST_VOTE, init=False)

@dataclass
class VoteCastMessage(NetworkMessage):
    player_id: int
    vote_choice: bool
    type: MessageType = field(default=MessageType.VOTE_CAST, init=False)

@dataclass
class RequestSabotageMessage(NetworkMessage):
    player_id: int
    type: MessageType = field(default=MessageType.REQUEST_SABOTAGE, init=False)

@dataclass
class SabotageChoiceMessage(NetworkMessage):
    player_id: int
    sabotage_choice: bool
    type: MessageType = field(default=MessageType.SABOTAGE_CHOICE, init=False)

@dataclass
class MissionOutcomeMessage(NetworkMessage):
    mission_success: bool
    sabotages_count: int
    type: MessageType = field(default=MessageType.MISSION_OUTCOME, init=False)

@dataclass
class GameOverMessage(NetworkMessage):
    winner: str
    type: MessageType = field(default=MessageType.GAME_OVER, init=False)

@dataclass
class LogMessage(NetworkMessage):
    text: str
    type: MessageType = field(default=MessageType.LOG_MESSAGE, init=False)

def create_message_from_dict(data: Dict[str, Any]) -> Optional[NetworkMessage]:
    msg_type_str = data.get("type")
    try:
        msg_type = MessageType(msg_type_str)
        if msg_type == MessageType.CONNECT_ACK:
            return ConnectAckMessage(player_id=data.get("player_id"))
        elif msg_type == MessageType.GAME_STATE_UPDATE:
            return GameStateUpdateMessage(state=data.get("state"))
        elif msg_type == MessageType.START_GAME:
            return StartGameMessage()
        elif msg_type == MessageType.PLAYER_ROLE:
            return PlayerRoleMessage(player_id=data.get("player_id"), role=data.get("role"))
        elif msg_type == MessageType.REQUEST_TEAM_SELECTION:
            return RequestTeamSelectionMessage(
                leader_id=data.get("leader_id"),
                mission_size=data.get("mission_size"),
                available_players_ids=data.get("available_players_ids")
            )
        elif msg_type == MessageType.TEAM_PROPOSED:
            return TeamProposedMessage(player_id=data.get("player_id"), team=data.get("team"))
        elif msg_type == MessageType.REQUEST_VOTE:
            return RequestVoteMessage(player_id=data.get("player_id"), team=data.get("team"))
        elif msg_type == MessageType.VOTE_CAST:
            return VoteCastMessage(player_id=data.get("player_id"), vote_choice=data.get("vote_choice"))
        elif msg_type == MessageType.REQUEST_SABOTAGE:
            return RequestSabotageMessage(player_id=data.get("player_id"))
        elif msg_type == MessageType.SABOTAGE_CHOICE:
            return SabotageChoiceMessage(player_id=data.get("player_id"), sabotage_choice=data.get("sabotage_choice"))
        elif msg_type == MessageType.MISSION_OUTCOME:
            return MissionOutcomeMessage(mission_success=data.get("mission_success"), sabotages_count=data.get("sabotages_count"))
        elif msg_type == MessageType.GAME_OVER:
            return GameOverMessage(winner=data.get("winner"))
        elif msg_type == MessageType.LOG_MESSAGE:
            return LogMessage(text=data.get("text"))
        else:
            return None
    except ValueError:
        print(f"Unknown message type string: {msg_type_str}")
        return None
    except KeyError as e:
        print(f"Missing key in message data for type {msg_type_str}: {e}. Data: {data}")
        return None
