"""
GitHub API client for repository and release operations.

Handles GitHub API interactions including repository info fetching,
release downloads, and rate limit management.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests

from src.config.constants import GITHUB_API_BASE
from src.models.github_info import GitHubRepo, GitHubRelease, GitHubAsset, GitHubContentItem
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GitHubClient:
    """
    GitHub API client with caching and rate limit handling.

    Provides methods for:
    - Fetching repository information
    - Getting releases and assets
    - Downloading release assets
    - Cloning repositories
    - Searching for IDA plugins
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client.

        Args:
            token: Optional GitHub personal access token for higher rate limits
        """
        self.token = token
        self.session = requests.Session()
        self.cache: dict = {}

        # Set up headers
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        self.session.headers.update(headers)

        # Rate limit tracking
        self.rate_limit_remaining = 60
        self.rate_limit_reset = 0

    def _check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits.

        Returns:
            True if we can make requests, False if rate limited
        """
        if self.rate_limit_remaining <= 1:
            now = int(time.time())
            if now < self.rate_limit_reset:
                wait_time = self.rate_limit_reset - now
                logger.warning(f"Rate limited. Waiting {wait_time} seconds")
                time.sleep(min(wait_time, 60))
        return True

    def _update_rate_limit(self, response: requests.Response) -> None:
        """
        Update rate limit info from response headers.

        Args:
            response: HTTP response object
        """
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")

        if remaining:
            self.rate_limit_remaining = int(remaining)
        if reset:
            self.rate_limit_reset = int(reset)

    def get_repository_info(self, owner: str, repo: str) -> Optional[GitHubRepo]:
        """
        Fetch repository information from GitHub.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            GitHubRepo object or None if failed
        """
        self._check_rate_limit()

        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        cache_key = f"repo:{owner}/{repo}"

        # Check cache
        if cache_key in self.cache:
            cached, timestamp = self.cache[cache_key]
            if time.time() - timestamp < 3600:  # 1 hour cache
                return cached

        try:
            response = self.session.get(url, timeout=30)
            self._update_rate_limit(response)
            response.raise_for_status()

            data = response.json()
            repo_info = GitHubRepo(
                id=data["id"],
                name=data["name"],
                full_name=data["full_name"],
                owner=data["owner"]["login"],
                description=data.get("description"),
                stars=data["stargazers_count"],
                topics=data.get("topics", []),
                language=data.get("language"),
                clone_url=data["clone_url"],
                html_url=data["html_url"],
                default_branch=data.get("default_branch", "main"),
                last_fetched=datetime.utcnow(),
            )

            # Cache the result
            self.cache[cache_key] = (repo_info, time.time())

            return repo_info

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch repository info: {e}")
            return None

    def get_releases(self, owner: str, repo: str) -> List[GitHubRelease]:
        """
        Fetch all releases for a repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of GitHubRelease objects
        """
        self._check_rate_limit()

        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases"

        try:
            response = self.session.get(url, timeout=30)
            self._update_rate_limit(response)
            response.raise_for_status()

            releases = []
            for data in response.json():
                assets = [
                    GitHubAsset(
                        name=asset["name"],
                        size=asset["size"],
                        download_url=asset["browser_download_url"],
                        content_type=asset["content_type"],
                    )
                    for asset in data.get("assets", [])
                ]

                release = GitHubRelease(
                    id=data["id"],
                    tag_name=data["tag_name"],
                    name=data.get("name"),
                    body=data.get("body"),
                    published_at=datetime.fromisoformat(data["published_at"].replace("Z", "+00:00"))
                    if data.get("published_at")
                    else None,
                    prerelease=data["prerelease"],
                    assets=assets,
                    html_url=data["html_url"],
                )
                releases.append(release)

            return releases

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch releases: {e}")
            return []

    def get_latest_release(self, owner: str, repo: str) -> Optional[GitHubRelease]:
        """
        Fetch the latest release for a repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            GitHubRelease object or None if no releases found
        """
        self._check_rate_limit()

        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases/latest"

        try:
            response = self.session.get(url, timeout=30)
            self._update_rate_limit(response)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()

            assets = [
                GitHubAsset(
                    name=asset["name"],
                    size=asset["size"],
                    download_url=asset["browser_download_url"],
                    content_type=asset["content_type"],
                )
                for asset in data.get("assets", [])
            ]

            return GitHubRelease(
                id=data["id"],
                tag_name=data["tag_name"],
                name=data.get("name"),
                body=data.get("body"),
                published_at=datetime.fromisoformat(data["published_at"].replace("Z", "+00:00"))
                if data.get("published_at")
                else None,
                prerelease=data["prerelease"],
                assets=assets,
                html_url=data["html_url"],
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch latest release: {e}")
            return None

    def get_readme(self, owner: str, repo: str, branch: str = "main") -> Optional[str]:
        """
        Fetch README content from repository.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name (default: "main")

        Returns:
            README content or None if not found
        """
        self._check_rate_limit()

        # Try common README filenames
        for readme_name in ["README.md", "README.rst", "README.txt"]:
            url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{readme_name}?ref={branch}"

            try:
                response = self.session.get(url, timeout=30)
                self._update_rate_limit(response)

                if response.status_code == 200:
                    data = response.json()
                    # README content is base64 encoded
                    import base64

                    content = base64.b64decode(data["content"]).decode("utf-8")
                    return content

            except requests.exceptions.RequestException:
                continue

        return None

    def get_repository_contents(
        self, owner: str, repo: str, path: str = "", branch: str = "main"
    ) -> List[GitHubContentItem]:
        """
        Fetch contents of a repository directory.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Directory path (empty for root)
            branch: Branch name (default: "main")

        Returns:
            List of GitHubContentItem objects
        """
        self._check_rate_limit()

        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}?ref={branch}"

        try:
            response = self.session.get(url, timeout=30)
            self._update_rate_limit(response)
            response.raise_for_status()

            items = []
            for data in response.json():
                item = GitHubContentItem(
                    name=data["name"],
                    path=data["path"],
                    type=data["type"],
                    size=data.get("size"),
                    download_url=data.get("download_url"),
                )
                items.append(item)

            return items

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch repository contents: {e}")
            return []

    def download_release_asset(
        self, download_url: str, destination: Path, timeout: int = 300
    ) -> Optional[Path]:
        """
        Download a release asset.

        Args:
            download_url: URL to download from
            destination: Destination file path
            timeout: Download timeout in seconds

        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # For large files, we might need to follow redirects
            response = self.session.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            # Ensure parent directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Download with progress
            downloaded = 0
            total_size = int(response.headers.get("content-length", 0))

            with open(destination, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if downloaded % (1024 * 1024) == 0:  # Log every MB
                                logger.debug(f"Download progress: {progress:.1f}%")

            logger.info(f"Downloaded {destination.name} ({downloaded} bytes)")
            return destination

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download asset: {e}")
            return None

    def search_ida_plugins(self, query: str = "topic:ida-pro-plugin language:python") -> List[GitHubRepo]:
        """
        Search GitHub for IDA Pro plugins.

        Args:
            query: Search query string

        Returns:
            List of GitHubRepo objects
        """
        self._check_rate_limit()

        url = f"{GITHUB_API_BASE}/search/repositories"
        params = {"q": query, "sort": "stars", "order": "desc", "per_page": 100}

        try:
            response = self.session.get(url, params=params, timeout=30)
            self._update_rate_limit(response)
            response.raise_for_status()

            repos = []
            for data in response.json().get("items", []):
                repo = GitHubRepo(
                    id=data["id"],
                    name=data["name"],
                    full_name=data["full_name"],
                    owner=data["owner"]["login"],
                    description=data.get("description"),
                    stars=data["stargazers_count"],
                    topics=data.get("topics", []),
                    language=data.get("language"),
                    clone_url=data["clone_url"],
                    html_url=data["html_url"],
                    default_branch=data.get("default_branch", "main"),
                    last_fetched=datetime.utcnow(),
                )
                repos.append(repo)

            return repos

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search repositories: {e}")
            return []

    def clone_repository(self, repo_url: str, destination: Path, branch: str = "main") -> bool:
        """
        Clone a GitHub repository using git.

        Args:
            repo_url: Repository URL
            destination: Destination directory
            branch: Branch to clone (default: "main")

        Returns:
            True if successful, False otherwise
        """
        try:
            import subprocess

            destination.parent.mkdir(parents=True, exist_ok=True)

            # Use git clone with shallow clone for speed
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(destination)],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                logger.info(f"Cloned repository to {destination}")
                return True
            else:
                logger.error(f"Git clone failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Git clone timed out")
            return False
        except FileNotFoundError:
            logger.error("Git not found in PATH")
            return False
        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            return False
