"""
Code browser example.

Run with:

    python code_browser.py PATH
"""

from __future__ import annotations

from jinja2 import Environment, FileSystemLoader

import sys

from rich.syntax import Syntax
from rich.traceback import Traceback

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll, Center
from textual.reactive import reactive, var
from textual.screen import Screen

from textual.widgets import ContentSwitcher, DirectoryTree, Footer, Header, Static, ListView, ListItem, Label, LoadingIndicator, Markdown, MarkdownViewer
from textual.widget import Widget

import asyncio
import STIGParser

class LoadingApp(LoadingIndicator):
    def __init__(self, message: str, **kwargs):
        super().__init__(**kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        with Center():
            yield Label(self.message, id="loading_text")
        yield LoadingIndicator()

class LoadSTIGs(Screen[dict]):
    def __init__(self, stig_parser) -> None:
        super().__init__()
        self.stig_parser = stig_parser

    def compose(self) -> ComposeResult:
        yield ListView(id="stig-list")
        yield LoadingApp("Initializing Application", id="loading")

    @work(thread=True)
    def build_stig_list(self):
        listview = {}
        for i in self.stig_parser.list_stigs():
            for j in self.stig_parser.list_versions(i):
                listview[j] = i
        self.app.call_from_thread(self.dismiss, listview)

    def on_mount(self) -> None:
        self.build_stig_list()

class STIG_List(ListView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class STIGViewer(App):
    """Textual code browser app."""

    CSS_PATH = "code_browser.tcss"
    BINDINGS = [
        ("f", "toggle_files", "Toggle Files"),
        ("q", "quit", "Quit"),
    ]

    show_tree = var(True)
    path: reactive[str | None] = reactive(None)
    stig_parser = STIGParser.STIGParser('U_SRG-STIG_Library_April_2026.zip')
    j2_env = Environment(loader=FileSystemLoader(f'./'))

    def watch_show_tree(self, show_tree: bool) -> None:
        """Called when show_tree is modified."""
        self.set_class(show_tree, "-show-tree")
        if show_tree:
            self.query_one(STIG_List).focus()

    def compose(self) -> ComposeResult:
        """Compose our UI."""        
        yield Header()
        with Container():
            yield STIG_List(id="stig-list")
            with ContentSwitcher(initial="code-view"):
                with VerticalScroll(id="code-view"):
                    yield MarkdownViewer(id="code")
                yield LoadingApp("Updating STIG Markdown", id="code-loading")
        yield Footer()

    def build_stig_list(self, listview: dict):
        self.stig_list = listview
        stig_list = self.query_one(STIG_List)
        categories = set(listview.values())
        categories = sorted(categories)
        for i in categories:
            stig_list.append(ListItem(Label(i), classes="stig_title"))
            for j in listview:
                if listview[j] == i:
                    stig_list.append(ListItem(Label(j), classes="stig_version"))
        stig_list.focus()

    def on_mount(self) -> None:
        self.title = "STIG Viewer"
        self.sub_title = "Select STIG to view"
        self.push_screen(LoadSTIGs(self.stig_parser), callback=self.build_stig_list)
        def theme_change(_signal) -> None:
            """Force the syntax to use a different theme."""
            self.watch_path(self.path)
        self.theme_changed_signal.subscribe(self, theme_change)

    async def update_stig_markdown(self, stig):
        stig_text = stig.item.children[0].renderable    
        code = self.query_one("#code", MarkdownViewer)
        self.sub_title = f"Loading {stig_text}"
        output_text = ""
        if "stig_version" in stig.item.classes:
            stig_file = self.get_stig(self.stig_list[stig_text], stig_text)
            stig_dict = self.stig_parser.parse_stig(stig_file)
            template = self.j2_env.get_template("rule.j2")
            output_text = template.render(stig = stig_dict)
        elif "stig_title" in stig.item.classes:
            output_text = f"# {stig_text}\n"
            for i in self.stig_list:
                if self.stig_list[i] == stig_text:
                    output_text += f"* {i}"
        code.document.update(output_text)
        self.query_one(ContentSwitcher).current = "code-view"
        self.sub_title = stig_text
        code.focus()


    async def on_list_view_selected(self, stig) -> None:
        if "stig_version" in stig.item.classes:
            stig_text = stig.item.children[0].renderable
            code_view = self.query_one("#code-view", VerticalScroll)
            self.query_one(ContentSwitcher).current = "code-loading"
            asyncio.create_task(self.update_stig_markdown(stig))
            

    def watch_path(self, path: str | None) -> None:
        code_view = self.query_one("#code", MarkdownViewer).document
        if path is None:
            code_view.update("")
            return
        code_view.update(path)
        self.subtitle = path

    def get_stig(self, stig, version) -> str:
        output = self.stig_parser.get_stig(stig, version)
        return output

    def action_toggle_files(self) -> None:
        """Called in response to key binding."""
        self.show_tree = not self.show_tree


if __name__ == "__main__":
    #STIGViewer().run()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    STIGViewer().run()
