import re
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class TextTag:
    tag_type: str = "text"

@dataclass
class ArtifactTag:
    tag_type: str = "artifact"
    artifact_type: str = "code"  # or "self_contained_text"
    identifier: str = ""
    title: str = ""
    language: Optional[str] = None

class ArtifactParser:
    def __init__(self):
        self.buffer = ""
        self.current_element = None
        self.current_tag = None
        self.tag_pattern = re.compile(r'<(artifact|text)[^>]*>|<(artifact|text)>')
        self.MALFORMED_CHECK_LENGTH = 100
    
    def feed(self, chunk: str) -> List[Tuple]:
        # Put implementation based on gallama parser here
        # Returns list of (tag, content) tuples
        pass