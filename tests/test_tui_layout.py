import asyncio
from ai_agent.ui.tui import AgentTUIApp

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
            print(f"H=14 files mode: Tree Region={tree.region}")
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
