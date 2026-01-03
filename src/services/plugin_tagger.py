"""
Plugin tagging service.

Automatically assigns tags to plugins based on:
- GitHub topics
- Repository description
- Code analysis
- Filename patterns
"""

import re
from typing import List, Optional, Set

from src.github.client import GitHubClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PluginTagger:
    """
    Automatic plugin tagging service.

    Analyzes plugin repositories and assigns relevant tags.
    """

    # Tag definitions with patterns
    TAG_DEFINITIONS = {
        "debugger": {
            "keywords": ["debug", "debugger", "breakpoint", "step", "trace"],
            "topics": ["debugging", "debugger"],
        },
        "decompiler": {
            "keywords": ["decompile", "decompiler", "pseudo", "pseudo-code"],
            "topics": ["decompiler", "decompilation"],
        },
        "hex-editor": {
            "keywords": ["hex", "hexadecimal", "binary", "byte"],
            "topics": ["hex-editor", "binary"],
        },
        "network": {
            "keywords": ["network", "protocol", "packet", "socket", "tcp", "udp"],
            "topics": ["network", "networking", "protocols"],
        },
        "analysis": {
            "keywords": ["analyze", "analysis", "static", "dynamic"],
            "topics": ["static-analysis", "dynamic-analysis", "reverse-engineering"],
        },
        "scripting": {
            "keywords": ["script", "python", "lua", "api", "automation"],
            "topics": ["scripting", "automation"],
        },
        "yara": {
            "keywords": ["yara", "rule", "signature"],
            "topics": ["yara", "malware-analysis"],
        },
        "graph": {
            "keywords": ["graph", "flowchart", "cfg", "call-graph", "visualization"],
            "topics": ["graph", "visualization"],
        },
        "patcher": {
            "keywords": ["patch", "patcher", "modify", "binary-patch"],
            "topics": ["patching", "binary-patching"],
        },
        "unpacker": {
            "keywords": ["unpack", "unpacker", "unpacking", "packer"],
            "topics": ["unpacking", "unpacker"],
        },
    }

    def __init__(self, github_client: GitHubClient):
        """
        Initialize plugin tagger.

        Args:
            github_client: GitHub API client
        """
        self.github_client = github_client

    def extract_tags(
        self,
        owner: str,
        repo: str,
        description: Optional[str] = None,
        readme_content: Optional[str] = None,
        topics: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Extract tags from plugin repository.

        Args:
            owner: Repository owner
            repo: Repository name
            description: Repository description (optional)
            readme_content: README content (optional)
            topics: GitHub topics (optional)

        Returns:
            List of tags
        """
        tags: Set[str] = set()

        # 1. Match GitHub topics to our tag system
        if topics:
            for topic in topics:
                tags.update(self._match_topic_to_tag(topic))

        # 2. Analyze description
        if description:
            tags.update(self._analyze_text(description))

        # 3. Analyze README
        if readme_content:
            tags.update(self._analyze_text(readme_content))

        # 4. Analyze repository name
        tags.update(self._analyze_repository_name(repo))

        return sorted(list(tags))

    def _match_topic_to_tag(self, topic: str) -> Set[str]:
        """Match GitHub topic to our tag system."""
        topic_lower = topic.lower()
        matched = set()

        for tag_name, definition in self.TAG_DEFINITIONS.items():
            if topic_lower in definition.get("topics", []):
                matched.add(tag_name)

        return matched

    def _analyze_text(self, text: str) -> Set[str]:
        """Analyze text for tag keywords."""
        text_lower = text.lower()
        tags = set()

        for tag_name, definition in self.TAG_DEFINITIONS.items():
            for keyword in definition.get("keywords", []):
                if keyword.lower() in text_lower:
                    tags.add(tag_name)

        return tags

    def _analyze_repository_name(self, repo_name: str) -> Set[str]:
        """Analyze repository name for hints."""
        name_lower = repo_name.lower()
        tags = set()

        # Common patterns in repo names
        if "debug" in name_lower:
            tags.add("debugger")
        if "hex" in name_lower or "binary" in name_lower:
            tags.add("hex-editor")
        if "decomp" in name_lower:
            tags.add("decompiler")
        if "unpack" in name_lower:
            tags.add("unpacker")
        if "patch" in name_lower:
            tags.add("patcher")

        return tags

    def update_plugin_tags(
        self,
        owner: str,
        repo: str,
        description: Optional[str] = None,
    ) -> List[str]:
        """
        Extract and update tags for a plugin.

        Args:
            owner: Repository owner
            repo: Repository name
            description: Repository description (optional)

        Returns:
            List of extracted tags
        """
        logger.info(f"Extracting tags for plugin: {owner}/{repo}")

        # Fetch repository info
        repo_info = self.github_client.get_repository_info(owner, repo)

        # Get topics
        topics = None
        if repo_info:
            topics = repo_info.topics

        # Fetch README
        readme = self.github_client.get_readme(owner, repo)

        # Extract tags
        tags = self.extract_tags(
            owner=owner,
            repo=repo,
            description=description,
            readme_content=readme,
            topics=topics,
        )

        logger.info(f"Extracted {len(tags)} tags: {tags}")
        return tags
