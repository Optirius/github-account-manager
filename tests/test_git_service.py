from pathlib import Path
from github_account_manager.models import Account, FolderMapping
from github_account_manager.services.git_service import GitService


def test_git_service_sync_and_includeif(tmp_path):
    gitconfig_path = tmp_path / ".gitconfig"
    # Seed with existing config
    gitconfig_path.write_text(
        "[core]\n\teditor = code\n[user]\n\tname = Default\n\temail = default@example.com\n",
        encoding="utf-8",
    )

    git_service = GitService(gitconfig_path=gitconfig_path, home_dir=tmp_path)

    acc1 = Account(
        id="acc-personal",
        name="Personal",
        email="personal@example.com",
        git_name="Personal Dev",
        ssh_key_path="C:/Users/ASUS/.ssh/id_ed25519_personal",
    )
    acc2 = Account(
        id="acc-work",
        name="Work",
        email="work@selise.com",
        git_name="Work Dev",
        ssh_key_path="C:/Users/ASUS/.ssh/id_ed25519_work",
    )

    mappings = [
        FolderMapping(folder_path="D:/Personal/", account_id="acc-personal"),
        FolderMapping(folder_path="D:/Professional/", account_id="acc-work"),
    ]

    success = git_service.sync_global_gitconfig([acc1, acc2], mappings)
    assert success is True

    content = gitconfig_path.read_text(encoding="utf-8")
    assert "[core]" in content
    assert 'includeIf "gitdir/i:D:/Personal/"' in content
    assert '.gitconfig-personal' in content
    assert 'includeIf "gitdir/i:D:/Professional/"' in content
    assert '.gitconfig-work' in content
