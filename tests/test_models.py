from github_account_manager.models import Account, FolderMapping, SSHKeyInfo, AppSettings


def test_account_model():
    acc = Account(
        name="Personal Account",
        email="personal@example.com",
        git_name="Personal Dev",
        username="tahmid95",
        ssh_key_path="C:/Users/user/.ssh/id_ed25519_personal",
    )
    assert acc.slug == "personal-account-tahmid95"
    assert acc.config_filename == ".gitconfig-personal-account-tahmid95"
    assert acc.username == "tahmid95"


def test_folder_mapping_normalization():
    m1 = FolderMapping(folder_path="D:\\Personal\\Projects", account_id="acc-1")
    assert m1.normalized_path == "D:/Personal/Projects/"

    m2 = FolderMapping(folder_path="D:/Professional/", account_id="acc-2")
    assert m2.normalized_path == "D:/Professional/"


def test_app_settings_serialization():
    settings = AppSettings(
        accounts=[
            Account(name="Work", email="work@test.com", git_name="Work User")
        ],
        folder_mappings=[
            FolderMapping(folder_path="D:/Work", account_id="123")
        ],
    )
    json_str = settings.model_dump_json()
    assert "work@test.com" in json_str
    assert "D:/Work" in json_str
