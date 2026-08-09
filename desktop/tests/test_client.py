import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Mock heavy dependencies completely to avoid installing them
import sys
sys.modules['cv2'] = MagicMock()
sys.modules['mediapipe'] = MagicMock()
sys.modules['mediapipe.solutions'] = MagicMock()

# Mock GUI and server libraries
sys.modules['webview'] = MagicMock()
sys.modules['uvicorn'] = MagicMock()
sys.modules['fastapi'] = MagicMock()
sys.modules['tkinter'] = MagicMock()

def test_main_desktop_initialization():
    try:
        from desktop.main_desktop import _get_log_dir, _check_single_instance
        
        # Test log dir creation
        log_dir = _get_log_dir()
        assert log_dir is not None
        assert os.path.exists(log_dir)
        
        # Test single instance (mocked)
        with patch('desktop.single_instance.acquire', return_value=True):
            assert _check_single_instance() == True
            
    except ImportError as e:
        pytest.fail(f"Could not import main_desktop: {e}")

def test_settings_manager():
    try:
        from desktop.settings_manager import load_settings, get_setting
        settings = load_settings()
        assert isinstance(settings, dict)
        assert get_setting('NO_HARDWARE') is not None
    except ImportError as e:
        pytest.fail(f"Could not import SettingsManager module: {e}")
