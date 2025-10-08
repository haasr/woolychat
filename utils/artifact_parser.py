import re
from dataclasses import dataclass
from typing import List, Tuple, Optional

ARTIFACT_SYSTEM_PROMPT = """ # Artifact System Instructions:
# Use artifacts for substantial, standalone content that users may reuse, modify, or reference. These are displayed in a separate UI window.

# ✅ Use artifacts for:
# - Content >12 lines (code, reports, full explanations)
# - Self-contained and reusable outputs
# - Deliverables for external use (e.g., presentations, emails)

# ❌ Avoid artifacts for:
# - Brief code, examples, math, or inline content
# - Explanations, feedback, or content tied to current context
# - One-off or simple responses

# 🧠 Usage Guidelines:
# - Prefer inline <text> content when artifacts aren't needed
# - One artifact per response unless requested otherwise
# - SVGs are acceptable responses to image requests

# 🛠️ Response Format:
# <answer>
#     <text>Optional intro or context</text>
#     <artifact identifier="unique-id" type="code|self_contained_text" language="python" title="Brief Title">
#     [Content here — no ``` for code, just raw]
#     </artifact>
# </answer>

# If artifacts are NOT used (e.g., on request or for simple content):
# <answer>
#     <text>
#     Regular content here.
#     ```python
#     # Code example
#     ```
#     </text>
# </answer>

# 📝 Notes:
# - Use kebab-case for `identifier`
# - Only these tags are allowed: <answer>, <text>, <artifact>
# - Markdown supported in <text> and `type="self_contained_text"`
# - No CDATA, no XML comments
# - Always acknowledge the user's prompt unless unnecessary

# End of Artifact System Instructions
#"""


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