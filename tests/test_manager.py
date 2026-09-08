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


def test_auto_repair_and_sync(tmp_path):
    config_file = tmp_path / "config.json"
    gitconfig = tmp_path / ".gitconfig"
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()

    personal_key = ssh_dir / "id_ed25519_personal"
    personal_key.write_text("personal_key_content", encoding="utf-8")
    (ssh_dir / "id_ed25519_personal.pub").write_text("ssh-ed25519 AAA... personal@example.com", encoding="utf-8")

    manager = AccountManager(
        config_file=config_file,
        gitconfig_path=gitconfig,
        ssh_dir=ssh_dir,
    )

    acc = manager.add_account(
        name="Personal Developer",
        email="personal@example.com",
        git_name="Personal Developer",
        username="user_personal",
        ssh_key_path=None,  # Intentionally null to test auto-repair
    )
    assert acc.ssh_key_path is None

    count, msgs = manager.auto_repair_and_sync()
    assert count >= 1
    assert acc.ssh_key_path == str(personal_key)


def test_link_ssh_key_to_account_and_lookup(tmp_path):
    config_file = tmp_path / "config.json"
    gitconfig = tmp_path / ".gitconfig"
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()

    key_a = ssh_dir / "id_ed25519_a"
    key_b = ssh_dir / "id_ed25519_b"
    key_a.write_text("key_a", encoding="utf-8")
    key_b.write_text("key_b", encoding="utf-8")

    manager = AccountManager(
        config_file=config_file,
        gitconfig_path=gitconfig,
        ssh_dir=ssh_dir,
    )

    acc1 = manager.add_account(name="Account 1", email="acc1@example.com", git_name="User 1")
    acc2 = manager.add_account(name="Account 2", email="acc2@example.com", git_name="User 2")

    assert manager.get_account_for_ssh_key(str(key_a)) is None

    # Link key_a to acc1
    ok, msg = manager.link_ssh_key_to_account(str(key_a), acc1.id)
    assert ok is True
    assert acc1.ssh_key_path == str(key_a)
    assert manager.get_account_for_ssh_key(str(key_a)).id == acc1.id

    # Reassign key_a to acc2 -> should unlink from acc1 and assign to acc2
    ok, msg = manager.link_ssh_key_to_account(str(key_a), acc2.id)
    assert ok is True
    assert acc1.ssh_key_path is None
    assert acc2.ssh_key_path == str(key_a)
    assert manager.get_account_for_ssh_key(str(key_a)).id == acc2.id

    # Unlink key_a by passing account_id=None
    ok, msg = manager.link_ssh_key_to_account(str(key_a), None)
    assert ok is True
    assert acc2.ssh_key_path is None
    assert manager.get_account_for_ssh_key(str(key_a)) is None



