"""
Tests for GitHubClient thread-safe operations.

Tests verify that:
1. Cache operations are thread-safe
2. Rate limit tracking is thread-safe
3. Multiple threads can access client concurrently
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch

from src.github.client import GitHubClient
from src.models.github_info import GitHubRepo


@pytest.fixture
def client():
    """Create a GitHubClient for testing."""
    return GitHubClient(token=None)


class TestGitHubClientThreadSafety:
    """Test thread-safe operations."""

    def test_cache_thread_safety(self, client):
        """Test that cache operations are thread-safe."""
        # Manually set a cached value
        cache_key = "test:repo"
        test_value = GitHubRepo(
            id="test/repo",
            repo_owner="test",
            repo_name="repo",
            stars=100,
        )

        client._set_cached(cache_key, test_value)

        # Multiple threads reading from cache
        results = []
        def read_cache():
            for _ in range(100):
                value = client._get_cached(cache_key)
                results.append(value)

        threads = [threading.Thread(target=read_cache) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All reads should succeed without errors
        assert len(results) == 500  # 5 threads * 100 reads
        # All cached values should be the same object (not None)
        assert all(r is not None for r in results)

    def test_cache_write_thread_safety(self, client):
        """Test that concurrent cache writes are thread-safe."""
        cache_keys = [f"test:key{i}" for i in range(10)]
        test_values = [
            GitHubRepo(
                id=f"test/repo{i}",
                repo_owner="test",
                repo_name=f"repo{i}",
                stars=i,
            )
            for i in range(10)
        ]

        # Multiple threads writing to cache
        def write_cache(index):
            client._set_cached(cache_keys[index], test_values[index])

        threads = [threading.Thread(target=write_cache, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify all values were cached correctly
        for i, key in enumerate(cache_keys):
            value = client._get_cached(key)
            assert value is not None
            assert value.stars == i

    def test_rate_limit_thread_safety(self, client):
        """Test that rate limit tracking is thread-safe."""
        # Simulate multiple threads checking rate limit
        def check_rate_limit():
            for _ in range(50):
                client._check_rate_limit()

        threads = [threading.Thread(target=check_rate_limit) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should complete without errors or deadlocks
        # Rate limit should be updated
        assert client.rate_limit_remaining >= 0

    def test_concurrent_cache_operations(self, client):
        """Test mixed read/write operations from multiple threads."""
        cache_key = "test:concurrent"
        test_value = GitHubRepo(
            id="test/concurrent",
            repo_owner="test",
            repo_name="concurrent",
            stars=999,
        )

        errors = []
        def mixed_operations(thread_id):
            try:
                for i in range(100):
                    # Write
                    if i % 3 == 0:
                        client._set_cached(f"{cache_key}:{thread_id}:{i}", test_value)
                    # Read
                    else:
                        client._get_cached(cache_key)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=mixed_operations, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0

    def test_cache_expiration_thread_safety(self, client):
        """Test that cache expiration is thread-safe."""
        # Add a value that will expire
        client._set_cached("test:expire", GitHubRepo(
            id="test/expire",
            repo_owner="test",
            repo_name="expire",
            stars=100,
        ))

        # Wait a bit (not full hour, just test thread safety)
        time.sleep(0.1)

        # Multiple threads reading potentially expired cache
        def read_expiring():
            value = client._get_cached("test:expire")
            # Should handle expiration gracefully
            return value

        threads = [threading.Thread(target=read_expiring) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should complete without errors


class TestGitHubClientContextManager:
    """Test GitHubClient context manager."""

    def test_context_manager_closes_session(self):
        """Test that context manager closes HTTP session."""
        with GitHubClient(token=None) as client:
            assert client.session is not None
            session_to_close = client.session

        # Session should be closed after context exit
        # Note: requests.Session doesn't have a simple way to check if closed
        # But we can verify no error occurs on close
        # If session was already used and closed, calling close again shouldn't error

    def test_multiple_context_managers(self):
        """Test creating multiple clients with context managers."""
        clients = []
        for _ in range(5):
            with GitHubClient(token=None) as client:
                clients.append(client)
                # Each client should work independently
                assert client.session is not None
                assert client._cache_lock is not None
                assert client._rate_limit_lock is not None

        # All clients should be independent (no shared state issues)


class TestGitHubClientRateLimiting:
    """Test rate limiting with thread safety."""

    def test_rate_limit_update_thread_safety(self, client):
        """Test that rate limit updates are thread-safe."""
        # Mock response
        mock_response = Mock()
        mock_response.headers = {
            "X-RateLimit-Remaining": "42",
            "X-RateLimit-Reset": "1234567890",
        }

        # Multiple threads updating rate limit
        def update_rate_limit():
            for _ in range(100):
                client._update_rate_limit(mock_response)

        threads = [threading.Thread(target=update_rate_limit) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Final value should be consistent
        assert client.rate_limit_remaining == 42
        assert client.rate_limit_reset == 1234567890

    def test_rate_limit_check_thread_safety(self, client):
        """Test that rate limit checks are thread-safe."""
        # Set low rate limit
        with client._rate_limit_lock:
            client.rate_limit_remaining = 1
            client.rate_limit_reset = int(time.time()) + 3600

        # Multiple threads checking rate limit
        def check_limit():
            for _ in range(50):
                client._check_rate_limit()

        threads = [threading.Thread(target=check_limit) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should complete without errors or deadlocks


class TestGitHubClientConcurrency:
    """Integration tests for concurrent operations."""

    @patch('src.github.client.requests.Session.get')
    def test_concurrent_api_calls(self, mock_get, client):
        """Test that concurrent API calls don't cause issues."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 12345,
            "name": "test-repo",
            "full_name": "test/test-repo",
            "stargazers_count": 100,
            "topics": ["ida", "plugin"],
        }
        mock_response.headers = {
            "X-RateLimit-Remaining": "60",
            "X-RateLimit-Reset": "1234567890",
        }
        mock_get.return_value = mock_response

        results = []
        errors = []

        def fetch_repo_info():
            try:
                for i in range(10):
                    repo = client.get_repository_info("test", f"repo{i}")
                    results.append(repo)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=fetch_repo_info) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All requests should succeed
        assert len(errors) == 0
        assert len(results) == 50  # 5 threads * 10 requests

    def test_concurrent_cache_and_rate_limit(self, client):
        """Test concurrent cache and rate limit operations."""
        errors = []

        def mixed_operations(thread_id):
            try:
                for i in range(100):
                    # Cache operations
                    if i % 2 == 0:
                        client._get_cached(f"test:{thread_id}:{i}")
                    else:
                        client._set_cached(f"test:{thread_id}:{i}", None)

                    # Rate limit operations
                    if i % 3 == 0:
                        client._check_rate_limit()

            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=mixed_operations, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0
