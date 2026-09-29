import asyncio
from pathlib import Path
from ai_agent.ui.tui import AgentTUIApp, ModelSelectModal, FilePreviewModal, ConfirmQuitModal

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
            # Dismiss modal with a new model
            app.screen.dismiss({
                "model": "nvidia/nemotron-3.5-lightning:free",
                "is_local": False,
                "base_url": None,
            })
            await pilot.pause()

            # Verify active model updated
            assert app.model == "nvidia/nemotron-3.5-lightning:free"
            assert app.agent.model == "nvidia/nemotron-3.5-lightning:free"
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
