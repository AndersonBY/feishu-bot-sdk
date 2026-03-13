"""Live integration tests for new/extended services.

Run with real credentials from ``E:/Projects/feishu-bot/.env``::

    cd E:/Projects/feishu-bot/feishu-bot-sdk
    uv run python -m pytest tests/integration/test_new_services_live.py -v -s

Each test creates its own resources, operates on them, and cleans up via
``try / finally`` so no garbage data is left behind even when assertions fail.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import pytest

from feishu_bot_sdk.bitable import BitableService
from feishu_bot_sdk.calendar import CalendarService
from feishu_bot_sdk.config import FeishuConfig
from feishu_bot_sdk.drive_files import DriveFileService
from feishu_bot_sdk.exceptions import ConfigurationError, HTTPRequestError
from feishu_bot_sdk.feishu import FeishuClient
from feishu_bot_sdk.sheets import SheetsService
from feishu_bot_sdk.task import TaskService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENV_PATH = Path("E:/Projects/feishu-bot/.env")


def _load_env() -> Dict[str, str]:
    """Parse the project .env file into a dict (key=value, ignoring blanks/comments)."""
    values: Dict[str, str] = {}
    if not _ENV_PATH.exists():
        return values
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key, value = key.strip(), value.strip()
        if key:
            values[key] = value
    return values


def _build_live_client() -> tuple[FeishuClient, Dict[str, str]]:
    """Build a *FeishuClient* from .env credentials or ``pytest.skip``."""
    env = _load_env()
    app_id = env.get("APP_ID") or env.get("FEISHU_APP_ID")
    app_secret = env.get("APP_SECRET") or env.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        pytest.skip("APP_ID / APP_SECRET not found in .env")

    auth_mode = (env.get("FEISHU_AUTH_MODE") or "tenant").strip().lower()
    user_token = env.get("FEISHU_USER_ACCESS_TOKEN") or None
    refresh_token = env.get("FEISHU_USER_REFRESH_TOKEN") or None

    config = FeishuConfig(
        app_id=app_id,
        app_secret=app_secret,
        auth_mode=auth_mode,
        user_access_token=user_token,
        user_refresh_token=refresh_token,
    )
    client = FeishuClient(config)
    return client, env


_AUTH_SKIP_CODES = {401, 403}


def _skip_on_auth_error(func):
    """Decorator: skip the test when credentials are expired/invalid or the
    API returns an auth-related HTTP error."""
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPRequestError as exc:
            # Some Feishu APIs return 404 for expired user tokens
            text = getattr(exc, "response_text", "") or ""
            is_auth = exc.status_code in _AUTH_SKIP_CODES or (
                exc.status_code == 404 and "token" in text.lower()
            )
            if is_auth:
                pytest.skip(f"Likely auth issue (HTTP {exc.status_code}): {exc}")
            raise
        except ConfigurationError as exc:
            pytest.skip(f"Configuration error: {exc}")

    return wrapper


def _get_open_id(env: Dict[str, str]) -> str:
    open_id = env.get("OPEN_ID") or env.get("FEISHU_OPEN_ID") or ""
    if not open_id:
        pytest.skip("OPEN_ID / FEISHU_OPEN_ID not found in .env")
    return open_id


def _print_response(label: str, resp: Any) -> None:
    if isinstance(resp, Mapping):
        summary = {k: (str(v)[:120] if isinstance(v, (str, list, dict)) else v) for k, v in resp.items()}
        print(f"  [{label}] {summary}")
    else:
        print(f"  [{label}] {resp}")


# ---------------------------------------------------------------------------
# Test 1 – Task full lifecycle
# ---------------------------------------------------------------------------

class TestTaskFullLifecycle:
    @_skip_on_auth_error
    def test_task_full_lifecycle(self) -> None:
        client, env = _build_live_client()
        svc = TaskService(client)
        task_guid: Optional[str] = None

        try:
            # 1. create task
            result = svc.create_task({"summary": "SDK Integration Test"})
            _print_response("create_task", result)
            task = result.get("task", {})
            task_guid = task.get("guid")
            assert task_guid, "create_task should return a task guid"
            print(f"  -> task_guid = {task_guid}")

            # 2. get task
            result = svc.get_task(task_guid)
            _print_response("get_task", result)
            assert result.get("task", {}).get("summary") == "SDK Integration Test"

            # 3. list tasks
            result = svc.list_tasks(page_size=5)
            _print_response("list_tasks", result)
            assert "items" in result

            # 4. update task
            result = svc.update_task(task_guid, {"summary": "Updated"}, update_fields=["summary"])
            _print_response("update_task", result)

            # 5. create subtask
            sub_result = svc.create_subtask(task_guid, {"summary": "Sub Item"})
            _print_response("create_subtask", sub_result)
            # API returns "subtask" key (not "task")
            subtask = sub_result.get("subtask", sub_result.get("task", {}))
            subtask_guid = subtask.get("guid")
            assert subtask_guid, "create_subtask should return a subtask guid"

            # 6. list subtasks
            sub_list = svc.list_subtasks(task_guid)
            _print_response("list_subtasks", sub_list)
            items = sub_list.get("items", [])
            assert isinstance(items, list) and len(items) > 0

            # 7. create comment
            comment_result = svc.create_comment(task_guid, "test comment")
            _print_response("create_comment", comment_result)
            comment = comment_result.get("comment", {})
            comment_id = comment.get("id")
            assert comment_id, "create_comment should return a comment id"

            # 8. list comments
            comments_list = svc.list_comments(task_guid)
            _print_response("list_comments", comments_list)
            assert "items" in comments_list

        finally:
            # 9. cleanup: mark task as completed (Task v2 has no delete API)
            if task_guid:
                try:
                    svc.update_task(
                        task_guid,
                        {"completed_at": str(int(time.time()))},
                        update_fields=["completed_at"],
                    )
                    print(f"  [cleanup] marked task {task_guid} as completed")
                except Exception as exc:
                    print(f"  [cleanup] failed to complete task: {exc}")


# ---------------------------------------------------------------------------
# Test 2 – TaskList lifecycle
# ---------------------------------------------------------------------------

class TestTasklistLifecycle:
    @_skip_on_auth_error
    def test_tasklist_lifecycle(self) -> None:
        client, env = _build_live_client()
        svc = TaskService(client)
        tasklist_guid: Optional[str] = None

        try:
            # 1. create tasklist
            result = svc.create_tasklist({"name": "SDK Test List"})
            _print_response("create_tasklist", result)
            tasklist = result.get("tasklist", {})
            tasklist_guid = tasklist.get("guid")
            assert tasklist_guid, "create_tasklist should return a tasklist guid"
            print(f"  -> tasklist_guid = {tasklist_guid}")

            # 2. get tasklist
            result = svc.get_tasklist(tasklist_guid)
            _print_response("get_tasklist", result)
            assert result.get("tasklist", {}).get("name") == "SDK Test List"

            # 3. list tasklists
            result = svc.list_tasklists(page_size=5)
            _print_response("list_tasklists", result)
            # items may be empty if tasklists are not returned in listing
            assert "items" in result or "has_more" in result

            # 4. update tasklist
            result = svc.update_tasklist(
                tasklist_guid, {"name": "Renamed"}, update_fields=["name"]
            )
            _print_response("update_tasklist", result)

        finally:
            # 5. cleanup: delete tasklist
            if tasklist_guid:
                try:
                    svc.delete_tasklist(tasklist_guid)
                    print(f"  [cleanup] deleted tasklist {tasklist_guid}")
                except Exception as exc:
                    print(f"  [cleanup] failed to delete tasklist: {exc}")


# ---------------------------------------------------------------------------
# Test 3 – Sheets full lifecycle
# ---------------------------------------------------------------------------

class TestSheetsFullLifecycle:
    @_skip_on_auth_error
    def test_sheets_full_lifecycle(self) -> None:
        client, env = _build_live_client()
        sheets_svc = SheetsService(client)
        drive_svc = DriveFileService(client)
        spreadsheet_token: Optional[str] = None

        try:
            # 1. create spreadsheet
            result = sheets_svc.create_spreadsheet(title="SDK Test Sheet")
            _print_response("create_spreadsheet", result)
            spreadsheet = result.get("spreadsheet", {})
            spreadsheet_token = spreadsheet.get("spreadsheet_token")
            assert spreadsheet_token, "create_spreadsheet should return a token"
            print(f"  -> spreadsheet_token = {spreadsheet_token}")

            # 2. get spreadsheet info
            info = sheets_svc.get_spreadsheet_info(spreadsheet_token)
            _print_response("get_spreadsheet_info", info)
            assert info.get("spreadsheet", {}).get("title") == "SDK Test Sheet"

            # 3. list sheets -> get first sheet_id
            sheets_result = sheets_svc.list_sheets(spreadsheet_token)
            _print_response("list_sheets", sheets_result)
            sheet_list = sheets_result.get("sheets", [])
            assert isinstance(sheet_list, list) and len(sheet_list) > 0
            sheet_id = sheet_list[0].get("sheet_id")
            assert sheet_id, "first sheet should have a sheet_id"
            print(f"  -> sheet_id = {sheet_id}")

            # 4. write values
            write_result = sheets_svc.write_values(
                spreadsheet_token,
                value_range={
                    "range": f"{sheet_id}!A1:B2",
                    "values": [["Name", "Score"], ["Alice", "100"]],
                },
            )
            _print_response("write_values", write_result)

            # 5. read values
            read_result = sheets_svc.read_values(spreadsheet_token, f"{sheet_id}!A1:B2")
            _print_response("read_values", read_result)
            value_range = read_result.get("valueRange", {})
            values = value_range.get("values", [])
            assert len(values) >= 2
            assert values[0][0] == "Name"
            assert values[1][0] == "Alice"

            # 6. append values
            append_result = sheets_svc.append_values(
                spreadsheet_token,
                value_range={
                    "range": f"{sheet_id}!A3:B3",
                    "values": [["Bob", "90"]],
                },
            )
            _print_response("append_values", append_result)

            # 7. find cells
            find_result = sheets_svc.find_cells(
                spreadsheet_token, sheet_id,
                find="Alice",
                find_condition={"range": f"{sheet_id}!A1:B10"},
            )
            _print_response("find_cells", find_result)
            find_list = find_result.get("find_result", {}).get("matched_cells", [])
            assert isinstance(find_list, list) and len(find_list) > 0

        finally:
            # 8. cleanup: delete the spreadsheet via drive
            if spreadsheet_token:
                try:
                    drive_svc.delete_file(spreadsheet_token, type="sheet")
                    print(f"  [cleanup] deleted sheet {spreadsheet_token}")
                except Exception as exc:
                    print(f"  [cleanup] failed to delete sheet: {exc}")


# ---------------------------------------------------------------------------
# Test 4 – Bitable app & views
# ---------------------------------------------------------------------------

class TestBitableAppAndViews:
    @_skip_on_auth_error
    def test_bitable_app_and_views(self) -> None:
        client, env = _build_live_client()
        bitable_svc = BitableService(client)
        drive_svc = DriveFileService(client)
        app_token: Optional[str] = None
        table_id: Optional[str] = None

        try:
            # 1. Create a bitable by creating a table inside a new app.
            #    First, create a folder-based bitable via drive, or use
            #    create_table on a fresh app.  The Feishu Bitable API requires
            #    an existing app_token.  We'll use the drive import approach:
            #    create a bitable file via drive, which gives us an app_token.
            #
            #    Actually the simplest way: use the drive API to create a bitable.
            #    But DriveFileService has no "create_bitable".  Let's use
            #    create_from_csv with a minimal CSV.
            import tempfile, os

            csv_content = "Name,Score\nAlice,100\nBob,90\n"
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", delete=False, encoding="utf-8"
            ) as f:
                f.write(csv_content)
                csv_path = f.name

            try:
                app_token, app_url = bitable_svc.create_from_csv(
                    csv_path, "SDK Test Bitable", "TestTable"
                )
            finally:
                os.unlink(csv_path)

            assert app_token, "create_from_csv should return app_token"
            print(f"  -> app_token = {app_token}, app_url = {app_url}")

            # Retrieve the actual table_id from the app
            tables_resp = bitable_svc.list_tables(app_token)
            table_items = tables_resp.get("items", [])
            assert isinstance(table_items, list) and len(table_items) > 0
            table_id = table_items[0].get("table_id")
            assert table_id, "should have at least one table"
            print(f"  -> table_id = {table_id}")

            # 2. get app
            app_info = bitable_svc.get_app(app_token)
            _print_response("get_app", app_info)
            assert app_info.get("app", {}).get("app_token") == app_token

            # 3. list views
            views_result = bitable_svc.list_views(app_token, table_id)
            _print_response("list_views", views_result)
            views_items = views_result.get("items", [])
            assert isinstance(views_items, list) and len(views_items) > 0, "should have default view"

            # 4. create view
            new_view = bitable_svc.create_view(
                app_token,
                table_id,
                {"view_name": "Test View", "view_type": "grid"},
            )
            _print_response("create_view", new_view)
            view = new_view.get("view", {})
            view_id = view.get("view_id")
            assert view_id, "create_view should return view_id"
            print(f"  -> view_id = {view_id}")

            # 5. get view
            got_view = bitable_svc.get_view(app_token, table_id, view_id)
            _print_response("get_view", got_view)
            assert got_view.get("view", {}).get("view_name") == "Test View"

            # 6. update view
            bitable_svc.update_view(
                app_token, table_id, view_id, {"view_name": "Renamed View"}
            )
            print("  [update_view] done")

            # 7. delete view
            bitable_svc.delete_view(app_token, table_id, view_id)
            print(f"  [delete_view] deleted {view_id}")

            # 8. get a field
            fields_result = bitable_svc.list_fields(app_token, table_id)
            _print_response("list_fields", fields_result)
            field_items = fields_result.get("items", [])
            assert isinstance(field_items, list) and len(field_items) > 0
            field_id = field_items[0].get("field_id")
            assert field_id
            try:
                field_info = bitable_svc.get_field(app_token, table_id, field_id)
                _print_response("get_field", field_info)
            except HTTPRequestError as exc:
                # get_field by ID may not be available for all field types
                print(f"  [get_field] skipped ({exc.status_code}): {exc}")

        finally:
            # 9. cleanup: delete the bitable via drive
            if app_token:
                try:
                    drive_svc.delete_file(app_token, type="bitable")
                    print(f"  [cleanup] deleted bitable {app_token}")
                except Exception as exc:
                    print(f"  [cleanup] failed to delete bitable: {exc}")


# ---------------------------------------------------------------------------
# Test 5 – Calendar attendees
# ---------------------------------------------------------------------------

class TestCalendarAttendees:
    @_skip_on_auth_error
    def test_calendar_attendees(self) -> None:
        client, env = _build_live_client()
        cal_svc = CalendarService(client)
        open_id = _get_open_id(env)
        calendar_id: Optional[str] = None
        event_id: Optional[str] = None

        try:
            # 1. primary calendar
            primary = cal_svc.primary_calendar()
            _print_response("primary_calendar", primary)
            calendars = primary.get("calendars", [])
            if isinstance(calendars, list) and len(calendars) > 0:
                calendar_id = calendars[0].get("calendar", {}).get("calendar_id")
            if not calendar_id:
                calendar_id = primary.get("calendar_id")
            assert calendar_id, "should find a primary calendar_id"
            print(f"  -> calendar_id = {calendar_id}")

            # 2. create event (1 hour from now)
            now_ts = int(time.time())
            event_data: dict[str, object] = {
                "summary": "SDK Test Event",
                "start_time": {"timestamp": str(now_ts + 3600)},
                "end_time": {"timestamp": str(now_ts + 7200)},
            }
            event_result = cal_svc.create_event(calendar_id, event_data)
            _print_response("create_event", event_result)
            event = event_result.get("event", {})
            event_id = event.get("event_id")
            assert event_id, "create_event should return event_id"
            print(f"  -> event_id = {event_id}")

            # 3. add attendee
            attendee_result = cal_svc.create_event_attendees(
                calendar_id,
                event_id,
                [{"type": "user", "user_id": open_id}],
                user_id_type="open_id",
            )
            _print_response("create_event_attendees", attendee_result)

            # 4. list attendees
            attendees_list = cal_svc.list_event_attendees(calendar_id, event_id)
            _print_response("list_event_attendees", attendees_list)
            att_items = attendees_list.get("items", [])
            assert isinstance(att_items, list) and len(att_items) > 0
            attendee_id = att_items[0].get("attendee_id")

            # 5. batch delete attendees
            if attendee_id:
                del_result = cal_svc.batch_delete_event_attendees(
                    calendar_id, event_id, [attendee_id]
                )
                _print_response("batch_delete_event_attendees", del_result)

            # 6. list event instances (for non-recurring this may return the event itself)
            try:
                instances = cal_svc.list_event_instances(calendar_id, event_id)
                _print_response("list_event_instances", instances)
            except Exception as exc:
                # Non-recurring events may not support instances
                print(f"  [list_event_instances] skipped (expected for non-recurring): {exc}")

        finally:
            # 7. cleanup: delete event
            if calendar_id and event_id:
                try:
                    cal_svc.delete_event(calendar_id, event_id)
                    print(f"  [cleanup] deleted event {event_id}")
                except Exception as exc:
                    print(f"  [cleanup] failed to delete event: {exc}")


# ---------------------------------------------------------------------------
# Test 6 – Drive list files & folder
# ---------------------------------------------------------------------------

class TestDriveListFilesAndFolder:
    @_skip_on_auth_error
    def test_drive_list_files_and_folder(self) -> None:
        client, env = _build_live_client()
        drive_svc = DriveFileService(client)
        folder_token: Optional[str] = None

        try:
            # 1. list files (root)
            result = drive_svc.list_files(page_size=5)
            _print_response("list_files (root)", result)
            # The response should have "files" key
            assert "files" in result or "items" in result

            # 2. create folder – need a parent folder token
            #    Use the root folder token from list_files or .env
            root_folder_token = env.get("FEISHU_ROOT_FOLDER_TOKEN", "")
            if not root_folder_token:
                # Try extracting from list_files response
                files = result.get("files", [])
                if isinstance(files, list) and len(files) > 0:
                    # Use any folder's parent_token, or fall back to empty string
                    root_folder_token = files[0].get("parent_token", "")

            if not root_folder_token:
                print("  [skip] no root folder token available for create_folder test")
            else:
                folder_result = drive_svc.create_folder(
                    name="SDK_Test_Folder", folder_token=root_folder_token
                )
                _print_response("create_folder", folder_result)
                folder_token = folder_result.get("token")
                assert folder_token, "create_folder should return a token"
                print(f"  -> folder_token = {folder_token}")

                # 3. list files in new folder (should be empty)
                inner = drive_svc.list_files(folder_token=folder_token)
                _print_response("list_files (new folder)", inner)
                inner_files = inner.get("files", [])
                assert isinstance(inner_files, list)
                assert len(inner_files) == 0, "new folder should be empty"

            # 4. iter_files smoke test
            count = 0
            for _file in drive_svc.iter_files(page_size=2):
                count += 1
                if count >= 3:
                    break
            print(f"  [iter_files] iterated {count} file(s)")

        finally:
            # 5. cleanup: delete folder
            if folder_token:
                try:
                    drive_svc.delete_file(folder_token, type="folder")
                    print(f"  [cleanup] deleted folder {folder_token}")
                except Exception as exc:
                    print(f"  [cleanup] failed to delete folder: {exc}")
