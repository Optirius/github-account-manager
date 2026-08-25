from pathlib import Path
from github_account_manager.services.manager import AccountManager


def test_manager_account_lifecycle(tmp_path):
    config_file = tmp_path / "config.json"
    gitconfig = tmp_path / ".gitconfig"
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()

    manager = AccountManager(
        config_file=config_file,
        gitconfig_path=gitconfig,
        ssh_dir=ssh_dir,
    )

    acc = manager.add_account(
        name="Freelance",
        email="freelance@example.com",
        git_name="Freelancer",
        username="freelance_user",
    )
    assert len(manager.settings.accounts) >= 1
    assert acc.email == "freelance@example.com"

    # Add folder mapping
    mapping = manager.add_folder_mapping("D:/Freelance", acc.id)
    assert mapping.account_id == acc.id

    # Check directory lookup
    matched = manager.get_account_for_folder("D:/Freelance/ClientProject")
    assert matched is not None
    assert matched.id == acc.id

    # Update account
    updated = manager.update_account(acc.id, email="new_email@example.com")
    assert updated is not None
    assert updated.email == "new_email@example.com"

    # Delete mapping
    removed = manager.remove_folder_mapping(mapping.id)
    assert removed is True
