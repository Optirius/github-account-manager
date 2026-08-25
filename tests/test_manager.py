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


def test_manager_delete_ssh_key_unlinks_account(tmp_path):
    config_file = tmp_path / "config.json"
    gitconfig = tmp_path / ".gitconfig"
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()

    priv = ssh_dir / "id_acc_key"
    pub = ssh_dir / "id_acc_key.pub"
    priv.write_text("priv", encoding="utf-8")
    pub.write_text("pub", encoding="utf-8")

    manager = AccountManager(
        config_file=config_file,
        gitconfig_path=gitconfig,
        ssh_dir=ssh_dir,
    )

    acc = manager.add_account(
        name="Personal",
        email="personal@example.com",
        git_name="Personal",
        ssh_key_path=str(priv),
    )
    assert acc.ssh_key_path == str(priv)

    deleted = manager.delete_ssh_key(str(priv))
    assert deleted is True
    assert not priv.exists()
    assert not pub.exists()

    # Verify unlinked from account
    refreshed_acc = next(a for a in manager.settings.accounts if a.id == acc.id)
    assert refreshed_acc.ssh_key_path is None

