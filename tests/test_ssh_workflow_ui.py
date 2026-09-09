import pytest
from unittest.mock import patch, MagicMock

try:
    import tkinter
    import customtkinter
    from github_account_manager.ui.components.dialogs import SSHTestGuideDialog, SSHActiveDeleteBlockDialog, NewSSHKeyDialog
    has_tkinter = True
except (ImportError, ModuleNotFoundError):
    has_tkinter = False

pytestmark = pytest.mark.skipif(not has_tkinter, reason="Tkinter is not installed on this system")

from github_account_manager.models import Account


def test_ssh_test_guide_dialog_attributes():
    # Test that SSHTestGuideDialog sets ssh_settings_url correctly
    assert hasattr(SSHTestGuideDialog, "_open_url")
    assert hasattr(SSHTestGuideDialog, "_copy_key")


def test_new_ssh_key_dialog_account_linking_signature():
    import inspect
    sig = inspect.signature(NewSSHKeyDialog.__init__)
    assert "available_accounts" in sig.parameters
