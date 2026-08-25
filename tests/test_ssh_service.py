from pathlib import Path
from github_account_manager.services.ssh_service import SSHService


def test_ssh_key_parsing(tmp_path):
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()

    # Create dummy pub key
    pub_file = ssh_dir / "id_ed25519_test.pub"
    pub_file.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestKey user@example.com", encoding="utf-8")

    priv_file = ssh_dir / "id_ed25519_test"
    priv_file.write_text("dummy-private-key", encoding="utf-8")

    service = SSHService(ssh_dir=ssh_dir)
    keys = service.list_keys()

    assert len(keys) == 1
    k = keys[0]
    assert k.name == "id_ed25519_test"
    assert k.key_type == "ED25519"
    assert k.comment == "user@example.com"
    assert "ITestKey" in (k.public_key_content or "")


def test_read_public_key(tmp_path):
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    pub_file = ssh_dir / "mykey.pub"
    pub_file.write_text("ssh-rsa AAAAB3NzaC1yc2E test@rsa.com", encoding="utf-8")

    service = SSHService(ssh_dir=ssh_dir)
    content = service.read_public_key(ssh_dir / "mykey")
    assert content == "ssh-rsa AAAAB3NzaC1yc2E test@rsa.com"


def test_delete_key(tmp_path):
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    priv = ssh_dir / "id_del"
    pub = ssh_dir / "id_del.pub"
    priv.write_text("priv", encoding="utf-8")
    pub.write_text("pub", encoding="utf-8")

    service = SSHService(ssh_dir=ssh_dir)
    assert priv.exists()
    assert pub.exists()

    res = service.delete_key(priv)
    assert res is True
    assert not priv.exists()
    assert not pub.exists()

