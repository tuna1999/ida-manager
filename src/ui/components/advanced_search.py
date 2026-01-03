"""
Advanced Search component for IDA Plugin Manager.

Provides advanced search and filtering capabilities with saved searches and search history.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Callable, List, Dict, Any

from src.models.plugin import PluginStatus, PluginType
from src.ui.spacing import Spacing
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AdvancedSearch:
    """
    Advanced search component with saved searches and search history.

    Features:
    - Text search with autocomplete
    - Multiple status filters (installed, not_installed, failed)
    - Type filters (legacy, modern)
    - Tag filters (multi-select)
    - Date range filters (7d, 30d, 90d, all)
    - Saved search presets
    - Search history (max 10)
    """

    # Available tags for filtering
    AVAILABLE_TAGS = [
        "debugger", "decompiler", "hex-editor", "network",
        "analysis", "scripting", "yara", "graph", "patcher", "unpacker"
    ]

    # Date range options
    DATE_RANGES = {
        "7d": 7,
        "30d": 30,
        "90d": 90,
        "all": None
    }

    def __init__(self, dpg, settings_manager):
        """
        Initialize the advanced search component.

        Args:
            dpg: Dear PyGui module reference
            settings_manager: SettingsManager instance for persistence
        """
        self.dpg = dpg
        self.settings = settings_manager

        # Generate unique instance ID for UUID-based tags
        self._instance_id = str(uuid.uuid4())[:8]

        # Filter state
        self._filter_text = ""
        self._selected_statuses: List[str] = []  # installed, not_installed, failed
        self._selected_types: List[str] = []  # legacy, modern
        self._selected_tags: List[str] = []
        self._date_range = "all"  # 7d, 30d, 90d, all

        # Saved searches and history
        self._saved_searches: Dict[str, Dict[str, Any]] = self._load_saved_searches()
        self._search_history: List[Dict[str, Any]] = self._load_search_history()

        # Callbacks
        self._on_search_callback: Optional[Callable] = None
        self._on_save_callback: Optional[Callable] = None

        # Tags
        self._container_tag = f"advanced_search_{self._instance_id}"
        self._search_input_tag = f"adv_search_input_{self._instance_id}"
        self._status_filter_tag = f"adv_status_filter_{self._instance_id}"
        self._type_filter_tag = f"adv_type_filter_{self._instance_id}"
        self._tag_filter_tag = f"adv_tag_filter_{self._instance_id}"
        self._date_range_tag = f"adv_date_range_{self._instance_id}"
        self._saved_searches_tag = f"adv_saved_searches_{self._instance_id}"
        self._search_history_tag = f"adv_search_history_{self._instance_id}"

    def create(self, parent_tag: str) -> None:
        """
        Create the advanced search UI.

        Args:
            parent_tag: Parent widget tag
        """
        dpg = self.dpg

        with dpg.group(tag=self._container_tag, parent=parent_tag):
            dpg.add_spacer(height=Spacing.SM)

            # Search input with history
            dpg.add_text("Search:")
            dpg.add_spacer(height=Spacing.XS)

            with dpg.group(horizontal=True):
                dpg.add_input_text(
                    hint="Search plugins by name...",
                    tag=self._search_input_tag,
                    width=-1,
                    callback=self._on_search_changed
                )
                dpg.add_spacer(width=Spacing.SM)
                dpg.add_button(label="Search", callback=self._execute_search, width=80)

            dpg.add_spacer(height=Spacing.SM)
            dpg.add_separator()
            dpg.add_spacer(height=Spacing.SM)

            # Status filters (multi-select)
            dpg.add_text("Status:")
            dpg.add_spacer(height=Spacing.XS)

            with dpg.group(horizontal=True):
                self._status_checkboxes = {}
                for status in ["installed", "not_installed", "failed"]:
                    checkbox_tag = f"adv_status_{status}_{self._instance_id}"
                    dpg.add_checkbox(
                        label=status.replace("_", " ").title(),
                        tag=checkbox_tag,
                        callback=lambda s, a, u, st=status: self._on_status_toggle(st)
                    )
                    self._status_checkboxes[status] = checkbox_tag

            dpg.add_spacer(height=Spacing.SM)

            # Type filters (multi-select)
            dpg.add_text("Type:")
            dpg.add_spacer(height=Spacing.XS)

            with dpg.group(horizontal=True):
                self._type_checkboxes = {}
                for ptype in ["legacy", "modern"]:
                    checkbox_tag = f"adv_type_{ptype}_{self._instance_id}"
                    dpg.add_checkbox(
                        label=ptype.title(),
                        tag=checkbox_tag,
                        callback=lambda s, a, u, pt=ptype: self._on_type_toggle(pt)
                    )
                    self._type_checkboxes[ptype] = checkbox_tag

            dpg.add_spacer(height=Spacing.SM)

            # Tag filters (multi-select)
            dpg.add_text("Tags:")
            dpg.add_spacer(height=Spacing.XS)

            with dpg.group(horizontal=True):
                self._tag_checkboxes = {}
                for i, tag in enumerate(self.AVAILABLE_TAGS[:5]):  # Show first 5
                    checkbox_tag = f"adv_tag_{tag}_{self._instance_id}"
                    dpg.add_checkbox(
                        label=f"[{tag}]",
                        tag=checkbox_tag,
                        callback=lambda s, a, u, t=tag: self._on_tag_toggle(t)
                    )
                    self._tag_checkboxes[tag] = checkbox_tag

            # More tags button
            dpg.add_spacer(width=Spacing.SM)
            dpg.add_button(label="More...", callback=self._show_more_tags, width=60)

            dpg.add_spacer(height=Spacing.SM)

            # Date range filter
            dpg.add_text("Date Updated:")
            dpg.add_spacer(height=Spacing.XS)

            with dpg.group(horizontal=True):
                self._date_radio_buttons = {}
                for range_name in ["7d", "30d", "90d", "all"]:
                    radio_tag = f"adv_date_{range_name}_{self._instance_id}"
                    label = "7 days" if range_name == "7d" else \
                           "30 days" if range_name == "30d" else \
                           "90 days" if range_name == "90d" else "All time"
                    dpg.add_radio_button(
                        label=label,
                        tag=radio_tag,
                        callback=lambda s, a, u, rn=range_name: self._on_date_range_change(rn)
                    )
                    self._date_radio_buttons[range_name] = radio_tag

            dpg.add_spacer(height=Spacing.MD)
            dpg.add_separator()
            dpg.add_spacer(height=Spacing.SM)

            # Action buttons
            with dpg.group(horizontal=True):
                dpg.add_button(label="Clear All", callback=self._clear_all_filters, width=100)
                dpg.add_spacer(width=Spacing.SM)
                dpg.add_button(label="Save Search", callback=self._save_search, width=100)
                dpg.add_spacer(width=Spacing.SM)
                dpg.add_button(label="Load Saved", callback=self._show_saved_searches, width=100)

            dpg.add_spacer(height=Spacing.SM)

            # Search history
            if self._search_history:
                dpg.add_separator()
                dpg.add_spacer(height=Spacing.SM)
                dpg.add_text("Recent Searches:")
                dpg.add_spacer(height=Spacing.XS)

                with dpg.group(tag=self._search_history_tag):
                    for i, search in enumerate(self._search_history[:5]):
                        search_label = search.get("text", "Search")[:20]
                        dpg.add_button(
                            label=f"{i+1}. {search_label}",
                            callback=lambda s, a, u, idx=i: self._load_history_item(idx),
                            width=-1
                        )

    def _on_search_changed(self, sender, app_data, user_data) -> None:
        """Handle search input change."""
        self._filter_text = app_data

    def _on_status_toggle(self, status: str) -> None:
        """Handle status checkbox toggle."""
        checkbox_tag = self._status_checkboxes[status]
        is_checked = self.dpg.get_value(checkbox_tag)

        if is_checked and status not in self._selected_statuses:
            self._selected_statuses.append(status)
        elif not is_checked and status in self._selected_statuses:
            self._selected_statuses.remove(status)

        logger.debug(f"Status filters: {self._selected_statuses}")

    def _on_type_toggle(self, ptype: str) -> None:
        """Handle type checkbox toggle."""
        checkbox_tag = self._type_checkboxes[ptype]
        is_checked = self.dpg.get_value(checkbox_tag)

        if is_checked and ptype not in self._selected_types:
            self._selected_types.append(ptype)
        elif not is_checked and ptype in self._selected_types:
            self._selected_types.remove(ptype)

        logger.debug(f"Type filters: {self._selected_types}")

    def _on_tag_toggle(self, tag: str) -> None:
        """Handle tag checkbox toggle."""
        checkbox_tag = self._tag_checkboxes.get(tag)
        if not checkbox_tag:
            return

        is_checked = self.dpg.get_value(checkbox_tag)

        if is_checked and tag not in self._selected_tags:
            self._selected_tags.append(tag)
        elif not is_checked and tag in self._selected_tags:
            self._selected_tags.remove(tag)

        logger.debug(f"Tag filters: {self._selected_tags}")

    def _on_date_range_change(self, range_name: str) -> None:
        """Handle date range radio button change."""
        self._date_range = range_name
        logger.debug(f"Date range: {self._date_range}")

    def _execute_search(self) -> None:
        """Execute search with current filters."""
        # Build filter dict
        filters = {
            "text": self._filter_text,
            "statuses": self._selected_statuses.copy(),
            "types": self._selected_types.copy(),
            "tags": self._selected_tags.copy(),
            "date_range": self._date_range
        }

        # Add to history
        self._add_to_history(filters)

        # Execute callback
        if self._on_search_callback:
            self._on_search_callback(filters)

        logger.info(f"Search executed with filters: {filters}")

    def _clear_all_filters(self) -> None:
        """Clear all filters."""
        # Uncheck all status checkboxes
        for status, tag in self._status_checkboxes.items():
            if self.dpg.does_item_exist(tag):
                self.dpg.set_value(tag, False)
        self._selected_statuses.clear()

        # Uncheck all type checkboxes
        for ptype, tag in self._type_checkboxes.items():
            if self.dpg.does_item_exist(tag):
                self.dpg.set_value(tag, False)
        self._selected_types.clear()

        # Uncheck all tag checkboxes
        for tag, checkbox_tag in self._tag_checkboxes.items():
            if self.dpg.does_item_exist(checkbox_tag):
                self.dpg.set_value(checkbox_tag, False)
        self._selected_tags.clear()

        # Clear search text
        if self.dpg.does_item_exist(self._search_input_tag):
            self.dpg.set_value(self._search_input_tag, "")
        self._filter_text = ""

        # Reset date range
        self._date_range = "all"

        logger.info("All filters cleared")

    def _save_search(self) -> None:
        """Save current search as a preset."""
        if not self._filter_text and not self._selected_statuses and not self._selected_tags:
            logger.warning("Cannot save empty search")
            return

        # Generate search name
        search_name = self._filter_text if self._filter_text else f"Search {len(self._saved_searches) + 1}"

        # Build filter dict
        filters = {
            "text": self._filter_text,
            "statuses": self._selected_statuses.copy(),
            "types": self._selected_types.copy(),
            "tags": self._selected_tags.copy(),
            "date_range": self._date_range
        }

        # Save to dict
        self._saved_searches[search_name] = filters
        self._save_saved_searches()

        logger.info(f"Search saved: {search_name}")

    def _show_saved_searches(self) -> None:
        """Show saved searches dialog."""
        # This would open a dialog with saved searches
        # For now, just log
        logger.info(f"Saved searches: {list(self._saved_searches.keys())}")

    def _load_saved_search(self, search_name: str) -> None:
        """Load a saved search."""
        if search_name not in self._saved_searches:
            logger.warning(f"Saved search not found: {search_name}")
            return

        filters = self._saved_searches[search_name]

        # Apply filters
        self._filter_text = filters.get("text", "")
        self._selected_statuses = filters.get("statuses", []).copy()
        self._selected_types = filters.get("types", []).copy()
        self._selected_tags = filters.get("tags", []).copy()
        self._date_range = filters.get("date_range", "all")

        # Update UI
        if self.dpg.does_item_exist(self._search_input_tag):
            self.dpg.set_value(self._search_input_tag, self._filter_text)

        for status in self._selected_statuses:
            checkbox_tag = self._status_checkboxes.get(status)
            if checkbox_tag and self.dpg.does_item_exist(checkbox_tag):
                self.dpg.set_value(checkbox_tag, True)

        for ptype in self._selected_types:
            checkbox_tag = self._type_checkboxes.get(ptype)
            if checkbox_tag and self.dpg.does_item_exist(checkbox_tag):
                self.dpg.set_value(checkbox_tag, True)

        for tag in self._selected_tags:
            checkbox_tag = self._tag_checkboxes.get(tag)
            if checkbox_tag and self.dpg.does_item_exist(checkbox_tag):
                self.dpg.set_value(checkbox_tag, True)

        logger.info(f"Loaded saved search: {search_name}")

    def _show_more_tags(self) -> None:
        """Show more tags dialog."""
        # This would open a dialog with all available tags
        logger.info("Show more tags dialog")

    def _add_to_history(self, filters: Dict[str, Any]) -> None:
        """Add search to history."""
        # Remove duplicate if exists
        self._search_history = [h for h in self._search_history if h != filters]

        # Add to front
        self._search_history.insert(0, filters)

        # Keep max 10
        if len(self._search_history) > 10:
            self._search_history = self._search_history[:10]

        # Save to settings
        self._save_search_history()

        # Refresh history display
        self._refresh_history_display()

    def _load_history_item(self, index: int) -> None:
        """Load a search history item."""
        if index >= len(self._search_history):
            return

        filters = self._search_history[index]

        # Apply filters
        self._filter_text = filters.get("text", "")
        self._selected_statuses = filters.get("statuses", []).copy()
        self._selected_types = filters.get("types", []).copy()
        self._selected_tags = filters.get("tags", []).copy()
        self._date_range = filters.get("date_range", "all")

        # Update UI
        if self.dpg.does_item_exist(self._search_input_tag):
            self.dpg.set_value(self._search_input_tag, self._filter_text)

        for status in self._selected_statuses:
            checkbox_tag = self._status_checkboxes.get(status)
            if checkbox_tag and self.dpg.does_item_exist(checkbox_tag):
                self.dpg.set_value(checkbox_tag, True)

        for ptype in self._selected_types:
            checkbox_tag = self._type_checkboxes.get(ptype)
            if checkbox_tag and self.dpg.does_item_exist(checkbox_tag):
                self.dpg.set_value(checkbox_tag, True)

        for tag in self._selected_tags:
            checkbox_tag = self._tag_checkboxes.get(tag)
            if checkbox_tag and self.dpg.does_item_exist(checkbox_tag):
                self.dpg.set_value(checkbox_tag, True)

        logger.info(f"Loaded history item: {index}")

    def _refresh_history_display(self) -> None:
        """Refresh the search history display."""
        if not self.dpg.does_item_exist(self._search_history_tag):
            return

        # Delete old history items
        self.dpg.delete_item(self._search_history_tag)

        # Recreate
        with self.dpg.group(tag=self._search_history_tag, parent=self._container_tag):
            for i, search in enumerate(self._search_history[:5]):
                search_label = search.get("text", "Search")[:20]
                self.dpg.add_button(
                    label=f"{i+1}. {search_label}",
                    callback=lambda s, a, u, idx=i: self._load_history_item(idx),
                    width=-1
                )

    def _load_saved_searches(self) -> Dict[str, Dict[str, Any]]:
        """Load saved searches from settings."""
        try:
            config = self.settings.load()
            return config.get("advanced_search", {}).get("saved", {})
        except Exception:
            return {}

    def _save_saved_searches(self) -> None:
        """Save saved searches to settings."""
        try:
            config = self.settings.load()
            if "advanced_search" not in config:
                config["advanced_search"] = {}
            config["advanced_search"]["saved"] = self._saved_searches
            self.settings.save(config)
        except Exception as e:
            logger.warning(f"Failed to save saved searches: {e}")

    def _load_search_history(self) -> List[Dict[str, Any]]:
        """Load search history from settings."""
        try:
            config = self.settings.load()
            return config.get("advanced_search", {}).get("history", [])
        except Exception:
            return []

    def _save_search_history(self) -> None:
        """Save search history to settings."""
        try:
            config = self.settings.load()
            if "advanced_search" not in config:
                config["advanced_search"] = {}
            config["advanced_search"]["history"] = self._search_history
            self.settings.save(config)
        except Exception as e:
            logger.warning(f"Failed to save search history: {e}")

    def set_callbacks(self, on_search: Optional[Callable] = None,
                     on_save: Optional[Callable] = None) -> None:
        """
        Set search callbacks.

        Args:
            on_search: Callback when search is executed
            on_save: Callback when search is saved
        """
        self._on_search_callback = on_search
        self._on_save_callback = on_save

    def get_filters(self) -> Dict[str, Any]:
        """Get current filter state."""
        return {
            "text": self._filter_text,
            "statuses": self._selected_statuses.copy(),
            "types": self._selected_types.copy(),
            "tags": self._selected_tags.copy(),
            "date_range": self._date_range
        }

    def get_tag(self) -> str:
        """Get the container tag."""
        return self._container_tag
