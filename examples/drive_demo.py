import argparse
import os
from pathlib import Path

from feishu_bot_sdk import DriveFileService, DrivePermissionService, FeishuClient, FeishuConfig

from _settings import load_settings


def build_client() -> FeishuClient:
    settings = load_settings()
    config = FeishuConfig(
        app_id=settings.app_id,
        app_secret=settings.app_secret,
        base_url=os.getenv("FEISHU_BASE_URL", "https://open.feishu.cn/open-apis"),
        member_permission=os.getenv("FEISHU_MEMBER_PERMISSION", "edit"),
    )
    return FeishuClient(config)


def main() -> None:
    parser = argparse.ArgumentParser(description="feishu_bot_sdk drive file/permission demo")
    parser.add_argument("--resource-token", required=True, help="Docx/Bitable file token")
    parser.add_argument("--resource-type", default="docx", help="docx/bitable/sheet/file/wiki")
    parser.add_argument("--member-id", required=True, help="Collaborator id")
    parser.add_argument("--member-id-type", default="open_id", help="open_id/user_id/union_id")
    parser.add_argument("--perm", default="edit", help="view/edit/full_access")
    parser.add_argument("--upload-file", help="Optional local file path to upload into Drive")
    parser.add_argument("--parent-type", default="explorer", help="Parent type for upload")
    parser.add_argument("--parent-node", help="Parent folder token for upload")
    args = parser.parse_args()

    client = build_client()
    permission = DrivePermissionService(client)
    permission.add_member(
        args.resource_token,
        resource_type=args.resource_type,
        member_id=args.member_id,
        member_id_type=args.member_id_type,
        perm=args.perm,
    )
    print("Collaborator granted.")

    if args.upload_file:
        if not args.parent_node:
            raise RuntimeError("--parent-node is required when --upload-file is provided")
        drive = DriveFileService(client)
        uploaded = drive.upload_file(
            str(Path(args.upload_file).resolve()),
            parent_type=args.parent_type,
            parent_node=args.parent_node,
        )
        print(f"Uploaded file token: {uploaded.get('file_token')}")


if __name__ == "__main__":
    main()
