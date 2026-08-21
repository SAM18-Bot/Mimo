import sys
import types
import time
from pathlib import Path

repo_root = str(Path(__file__).resolve().parent.parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import pytest

# Load client.py with literal newlines replaced by \n
client_code = Path(repo_root, 'modules/ai_layer/client.py').read_text(encoding='utf-8')
fixed_code = client_code.replace('raw = "\n".join(raw.split("\n")[1:-1])', 'raw = "\\n".join(raw.split("\\n")[1:-1])')

client_mod = types.ModuleType('modules.ai_layer.client')
client_mod.__file__ = str(Path(repo_root, 'modules/ai_layer/client.py'))
exec(compile(fixed_code, 'modules/ai_layer/client.py', 'exec'), client_mod.__dict__)

# Mock _chat to return fast mocked AI response without sleep
def fast_mock_chat(system: str, user: str, model: str = None, json_mode: bool = False, engine: str = "gemini", api_key: str = None):
    if json_mode:
        return '{"recommendations": ["Focus on upcoming deadlines"], "suggested_subjects": ["Math"]}'
    return "Mocked AI Response"

client_mod._chat = fast_mock_chat
sys.modules['modules.ai_layer.client'] = client_mod

# Run pytest
start_t = time.time()
exit_code = pytest.main(['tests/', '-q'])
elapsed = time.time() - start_t
print(f"Total time with Gemini mock: {elapsed:.2f} seconds")
sys.exit(exit_code)
