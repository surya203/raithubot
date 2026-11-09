from pathlib import Path

from app.errors import ConfigurationError

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


class PromptManager:
    def load(self, name: str) -> str:
        path = PROMPTS_DIR / name
        if not path.is_file():
            raise ConfigurationError(f"Prompt file {name} is missing.")
        return path.read_text(encoding="utf-8").strip()
