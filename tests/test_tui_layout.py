import asyncio
from pathlib import Path
from textual.widgets import Button, Input, Label
from ai_agent.ui.tui import AgentTUIApp, ModelSelectModal, FilePreviewModal, ConfirmQuitModal, KeysModal

def test_tui_small_mode_workspace_files():
    async def _run():
        # Terminal with only 14 lines
        app = AgentTUIApp()
        async with app.run_test(size=(100, 14)) as pilot:
            await pilot.pause()
            # In small terminal, app starts in 'files' mode
            files_box = app.query_one("#files-box")
            tool_box = app.query_one("#tool-box")
            tree = app.query_one("#file-tree")
            status = app.query_one("#status-bar")

            assert files_box.display is True
            assert tool_box.display is False
            assert status is not None

            # Verify the tree is fully visible with substantial height
            assert tree.region.height >= 5
            # Make sure it does not overflow past the screen height
            assert tree.region.y + tree.region.height <= 14

            # Switch to tools mode
            app.action_view_tools()
            await pilot.pause()
            assert files_box.display is False
            assert tool_box.display is True
            tlog = app.query_one("#tool-log")
            assert tlog.region.height >= 5

            # Switch to split mode
            app.action_view_split()
            await pilot.pause()
            assert files_box.display is True
            assert tool_box.display is True

            # Switch back to files
            app.action_view_files()
            await pilot.pause()
            assert files_box.display is True
            assert tool_box.display is False

    asyncio.run(_run())


def test_tui_tall_mode():
    async def _run():
        # Standard 24 line terminal
        app = AgentTUIApp()
        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            files_box = app.query_one("#files-box")
            tool_box = app.query_one("#tool-box")
            # Starts in split mode when height >= 18
            assert files_box.display is True
            assert tool_box.display is True
    asyncio.run(_run())


def test_tui_model_switcher_modal():
    async def _run():
        app = AgentTUIApp()
        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            # Trigger model switch modal
            app.action_switch_model()
            await pilot.pause()

            # Verify modal is active
            assert isinstance(app.screen, ModelSelectModal)
            custom_input = app.screen.query_one("#custom-model-input", Input)
            confirm_btn = app.screen.query_one("#btn-confirm-model", Button)

            # Test invalid model ID (e.g. 'asd')
            custom_input.value = "asd"
            confirm_btn.press()
            await pilot.pause()
            # Modal must NOT dismiss
            assert isinstance(app.screen, ModelSelectModal)
            err_lbl = app.screen.query_one("#model-error-msg", Label)
            assert err_lbl.display is True

            # Test valid model ID (e.g. 'openai/gpt-4o')
            custom_input.value = "openai/gpt-4o"
            confirm_btn.press()
            await pilot.pause()
            # Modal must dismiss and update active model
            assert not isinstance(app.screen, ModelSelectModal)
            assert app.model == "openai/gpt-4o"
            assert app.agent.model == "openai/gpt-4o"

            # Re-open and verify close [ X ] button
            app.action_switch_model()
            await pilot.pause()
            assert isinstance(app.screen, ModelSelectModal)
            close_btn = app.screen.query_one("#btn-close-model", Button)
            assert close_btn.label == "X"
            close_btn.press()
            await pilot.pause()
            assert not isinstance(app.screen, ModelSelectModal)

        # Verify model modal renders properly without clipping on small terminal height
        app_small = AgentTUIApp()
        async with app_small.run_test(size=(80, 14)) as small_pilot:
            await small_pilot.pause()
            app_small.action_switch_model()
            await small_pilot.pause()
            assert isinstance(app_small.screen, ModelSelectModal)
            confirm = app_small.screen.query_one("#btn-confirm-model", Button)
            dialog = app_small.screen.query_one("#model-dialog")
            assert confirm.region.y + confirm.region.height <= dialog.region.y + dialog.region.height
            app_small.screen.dismiss(None)
    asyncio.run(_run())


def test_tui_file_preview_modal():
    async def _run():
        app = AgentTUIApp()
        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            # Open file preview for pyproject.toml
            test_file = app.workspace_dir / "pyproject.toml"
            if test_file.exists():
                app.open_file_preview(test_file)
                await pilot.pause()
                assert isinstance(app.screen, FilePreviewModal)
                # Dismiss modal
                app.screen.dismiss()
                await pilot.pause()
                assert not isinstance(app.screen, FilePreviewModal)
    asyncio.run(_run())


def test_tui_confirm_quit_modal():
    async def _run():
        app = AgentTUIApp()
        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            # Trigger quit action
            app.action_quit_app()
            await pilot.pause()
            assert isinstance(app.screen, ConfirmQuitModal)
            # Cancel quit
            app.screen.dismiss(False)
            await pilot.pause()
            assert not isinstance(app.screen, ConfirmQuitModal)
    asyncio.run(_run())


def test_tui_chat_expand_toggle():
    async def _run():
        app = AgentTUIApp()
        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            chat = app.query_one("#chat-container")
            sidebar = app.query_one("#sidebar")
            assert sidebar.display is True

            # Toggle expand chat
            app.action_toggle_chat_expand()
            await pilot.pause()
            assert sidebar.display is False
            assert app.is_chat_expanded is True

            # Restore
            app.action_toggle_chat_expand()
            await pilot.pause()
            assert sidebar.display is True
            assert app.is_chat_expanded is False
    asyncio.run(_run())


def test_tui_bottom_bar_actions():
    async def _run():
        app = AgentTUIApp()
        async with app.run_test(size=(120, 24)) as pilot:
            await pilot.pause()
            # Verify bottom bar and buttons exist
            bottom_bar = app.query_one("#bottom-bar")
            btn_files = app.query_one("#btn-view-files")
            btn_tools = app.query_one("#btn-view-tools")
            btn_split = app.query_one("#btn-view-split")
            btn_chat = app.query_one("#expand-chat-btn")
            btn_palette = app.query_one("#btn-palette")
            btn_quit = app.query_one("#quit-btn")
            assert bottom_bar is not None
            assert btn_files is not None
            assert btn_quit is not None
            assert btn_palette.label == "PALETTE"

            # Click TOOLS button
            await pilot.click("#btn-view-tools")
            await pilot.pause()
            assert app.current_view_mode == "tools"
            assert "bottom-btn-active" in btn_tools.classes

            # Click FILES button
            await pilot.click("#btn-view-files")
            await pilot.pause()
            assert app.current_view_mode == "files"
            assert "bottom-btn-active" in btn_files.classes

            # Click SPLIT button
            await pilot.click("#btn-view-split")
            await pilot.pause()
            assert app.current_view_mode == "split"
            assert "bottom-btn-active" in btn_split.classes

            # Click CHAT button to expand full-width
            btn_chat.press()
            await pilot.pause()
            assert app.is_chat_expanded is True
            assert btn_chat.label == "RESTORE"

            # Click again to restore
            btn_chat.press()
            await pilot.pause()
            assert app.is_chat_expanded is False
            assert btn_chat.label == "CHAT"

            # Click PALETTE button to open Command Palette
            btn_palette.press()
            await pilot.pause()
            from textual.command import CommandPalette
            assert isinstance(app.screen, CommandPalette)
            # Verify red [ X ] button exists on the palette
            palette_close_btn = app.screen.query_one("#btn-close-palette", Button)
            assert palette_close_btn.label == "X"
            palette_close_btn.press()
            await pilot.pause()
            assert not isinstance(app.screen, CommandPalette)

            # Click QUIT button to open ConfirmQuitModal
            btn_quit.press()
            await pilot.pause()
            assert isinstance(app.screen, ConfirmQuitModal)
            app.screen.dismiss(False)
            await pilot.pause()

    asyncio.run(_run())


def test_tui_keys_modal():
    async def _run():
        app = AgentTUIApp()
        async with app.run_test(size=(120, 24)) as pilot:
            await pilot.pause()
            # Trigger help action (F1 or keys)
            app.action_help()
            await pilot.pause()
            assert isinstance(app.screen, KeysModal)

            # Check close button X
            close_btn = app.screen.query_one("#btn-close-keys", Button)
            assert close_btn.label == "X"
            close_btn.press()
            await pilot.pause()
            assert not isinstance(app.screen, KeysModal)

            # Open Command Palette and trigger Keys
            await pilot.press("alt+p")
            await pilot.pause(0.2)
            await pilot.press("enter")
            await pilot.pause(0.3)
            assert isinstance(app.screen, KeysModal)
            keys_close = app.screen.query_one("#btn-close-keys", Button)
            keys_close.press()
            await pilot.pause()
            assert not isinstance(app.screen, KeysModal)
    asyncio.run(_run())


def test_tui_screen_fit_dimensions():
    async def _run():
        for height in (20, 24, 30):
            app = AgentTUIApp()
            async with app.run_test(size=(100, height)) as pilot:
                await pilot.pause()
                main_c = app.query_one("#main-container")
                bottom = app.query_one("#bottom-bar")
                # Bottom bar touches the exact bottom row
                assert bottom.region.y + bottom.region.height == height
                # Main container does not overflow below screen height
                assert main_c.region.y + main_c.region.height <= height

                # Verify SEND button is compact and does not overlap
                send_btn = app.query_one("#send-btn")
                assert send_btn.region.width <= 10

                # Verify HeaderIcon on top of status is hidden
                from textual.widgets._header import HeaderIcon
                header_icon = app.query_one(HeaderIcon)
                assert header_icon.display is False

                # Verify StaticHeader cannot be clicked to expand
                from ai_agent.ui.tui import StaticHeader
                header = app.query_one(StaticHeader)
                assert header.region.height == 1
                await pilot.click(StaticHeader)
                await pilot.pause()
                assert header.region.height == 1
                assert not header.has_class("-tall")
    asyncio.run(_run())
