import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _default_clock():
    return datetime.now(timezone.utc).isoformat()


def _default_uuid():
    return str(uuid.uuid4())


def _title(conversation):
    for message in conversation["messages"]:
        if message["role"] == "user":
            return message["content"]
    return "(no messages)"


class History:
    def __init__(self, path, *, clock=None, uuid_factory=None):
        self.path = Path(path)
        self._clock = clock or _default_clock
        self._uuid = uuid_factory or _default_uuid
        if self.path.exists():
            self.state = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.state = {"conversations": []}

    def new_conversation(self, model):
        now = self._clock()
        conversation = {
            "id": self._uuid(),
            "created_at": now,
            "updated_at": now,
            "model": model,
            "messages": [],
        }
        self.state["conversations"].append(conversation)
        return conversation

    def _ordered(self):
        return sorted(
            self.state["conversations"],
            key=lambda c: c["updated_at"],
            reverse=True,
        )

    def most_recent(self):
        ordered = self._ordered()
        return ordered[0] if ordered else None

    def select(self, index):
        ordered = self._ordered()
        if index < 1 or index > len(ordered):
            raise IndexError(
                f"conversation {index} out of range (valid: 1..{len(ordered)})"
            )
        return ordered[index - 1]

    def append_turn(self, conversation, user_msg, assistant_msg):
        conversation["messages"].append({"role": "user", "content": user_msg})
        conversation["messages"].append({"role": "assistant", "content": assistant_msg})
        conversation["updated_at"] = self._clock()

    def list_recent(self, limit):
        return [
            (i, _title(conversation))
            for i, conversation in enumerate(self._ordered()[:limit], start=1)
        ]

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
