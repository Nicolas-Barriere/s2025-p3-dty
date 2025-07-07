from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from enum import Enum


@dataclass
class Email:
    datetime: str
    sender: str
    recipients: List[str]

    id: str = field(default_factory=lambda: str(datetime.now().timestamp()))
    cc: List[str] = field(default_factory=list)
    subject: str = "Aucun objet"
    body: str = ""
    attachments: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    summary: str = ""


class Tag(Enum):
    URGENT = 0
    DEFERRED = 1
    IRRELEVANT = 2

    def __str__(self) -> str:
        return self.name
