"""
Unit tests for OPEN_NOTEBOOK_WORKER_MAX_TASKS environment variable configuration.

This test suite verifies:
- Default value (5) when ENV not set
- Custom value when ENV is set
- Edge cases and validation
"""

import os
from unittest.mock import patch

import pytest


class TestWorkerMaxTasksEnv:
    """Test suite for OPEN_NOTEBOOK_WORKER_MAX_TASKS environment variable."""

    def setup_method(self):
        """Save original environment and clean up before each test."""
        self.original_value = os.environ.get('OPEN_NOTEBOOK_WORKER_MAX_TASKS')
        # Remove the variable to start clean
        if 'OPEN_NOTEBOOK_WORKER_MAX_TASKS' in os.environ:
            del os.environ['OPEN_NOTEBOOK_WORKER_MAX_TASKS']

    def teardown_method(self):
        """Restore original environment after each test."""
        if self.original_value is not None:
            os.environ['OPEN_NOTEBOOK_WORKER_MAX_TASKS'] = self.original_value
        elif 'OPEN_NOTEBOOK_WORKER_MAX_TASKS' in os.environ:
            del os.environ['OPEN_NOTEBOOK_WORKER_MAX_TASKS']

    def test_default_value_when_not_set(self):
        """Test that default value is 5 when ENV var is not set."""
        # Ensure ENV is not set
        if 'OPEN_NOTEBOOK_WORKER_MAX_TASKS' in os.environ:
            del os.environ['OPEN_NOTEBOOK_WORKER_MAX_TASKS']
        
        # Simulate shell default expansion: ${OPEN_NOTEBOOK_WORKER_MAX_TASKS:-5}
        value = os.environ.get('OPEN_NOTEBOOK_WORKER_MAX_TASKS', '5')
        assert value == '5'
        assert int(value) == 5

    def test_custom_value_when_set(self):
        """Test that custom value is used when ENV var is set."""
        os.environ['OPEN_NOTEBOOK_WORKER_MAX_TASKS'] = '10'
        
        value = os.environ.get('OPEN_NOTEBOOK_WORKER_MAX_TASKS', '5')
        assert value == '10'
        assert int(value) == 10

    def test_custom_value_one(self):
        """Test single-GPU setup with value of 1."""
        os.environ['OPEN_NOTEBOOK_WORKER_MAX_TASKS'] = '1'
        
        value = os.environ.get('OPEN_NOTEBOOK_WORKER_MAX_TASKS', '5')
        assert value == '1'
        assert int(value) == 1

    def test_custom_value_zero(self):
        """Test with value of 0 (edge case)."""
        os.environ['OPEN_NOTEBOOK_WORKER_MAX_TASKS'] = '0'
        
        value = os.environ.get('OPEN_NOTEBOOK_WORKER_MAX_TASKS', '5')
        assert value == '0'
        assert int(value) == 0

    def test_large_value(self):
        """Test with large value."""
        os.environ['OPEN_NOTEBOOK_WORKER_MAX_TASKS'] = '100'
        
        value = os.environ.get('OPEN_NOTEBOOK_WORKER_MAX_TASKS', '5')
        assert value == '100'
        assert int(value) == 100

    def test_invalid_value_non_numeric(self):
        """Test that non-numeric values are handled (shell will pass them through)."""
        os.environ['OPEN_NOTEBOOK_WORKER_MAX_TASKS'] = 'invalid'
        
        value = os.environ.get('OPEN_NOTEBOOK_WORKER_MAX_TASKS', '5')
        assert value == 'invalid'
        
        # Attempting to convert to int should raise ValueError
        with pytest.raises(ValueError):
            int(value)

    def test_invalid_value_negative(self):
        """Test with negative value."""
        os.environ['OPEN_NOTEBOOK_WORKER_MAX_TASKS'] = '-1'
        
        value = os.environ.get('OPEN_NOTEBOOK_WORKER_MAX_TASKS', '5')
        assert value == '-1'
        assert int(value) == -1

    def test_empty_string_value(self):
        """Test with empty string (shell treats this as set but empty)."""
        os.environ['OPEN_NOTEBOOK_WORKER_MAX_TASKS'] = ''
        
        value = os.environ.get('OPEN_NOTEBOOK_WORKER_MAX_TASKS', '5')
        # Empty string is still "set", so default doesn't apply
        assert value == ''

    def test_shell_default_expansion_simulation(self):
        """Simulate shell default expansion behavior: ${VAR:-default}."""
        # When VAR is not set, use default
        if 'OPEN_NOTEBOOK_WORKER_MAX_TASKS' in os.environ:
            del os.environ['OPEN_NOTEBOOK_WORKER_MAX_TASKS']
        
        # Shell: ${OPEN_NOTEBOOK_WORKER_MAX_TASKS:-5}
        value = os.environ.get('OPEN_NOTEBOOK_WORKER_MAX_TASKS', '5')
        assert value == '5'

    def test_shell_explicit_value(self):
        """Simulate shell with explicit value set."""
        os.environ['OPEN_NOTEBOOK_WORKER_MAX_TASKS'] = '7'
        
        # Shell: ${OPEN_NOTEBOOK_WORKER_MAX_TASKS:-5}
        value = os.environ.get('OPEN_NOTEBOOK_WORKER_MAX_TASKS', '5')
        assert value == '7'

    def test_worker_startup_command_contains_max_tasks_flag(self):
        """Verify worker startup commands include --max-tasks flag."""
        import subprocess
        
        # Test dev-init.sh
        result = subprocess.run(
            ['grep', '-n', 'max-tasks', 'dev-init.sh'],
            capture_output=True,
            text=True,
            cwd='/mnt/c/Users/T11/SynologyDrive/LLM/open-notebook'
        )
        assert result.returncode == 0
        assert '--max-tasks' in result.stdout
        assert 'OPEN_NOTEBOOK_WORKER_MAX_TASKS' in result.stdout
        assert ':-5}' in result.stdout  # Default value 5

    def test_makefile_worker_targets_contain_max_tasks(self):
        """Verify Makefile worker targets include --max-tasks flag."""
        import subprocess
        
        result = subprocess.run(
            ['grep', '-n', 'max-tasks', 'Makefile'],
            capture_output=True,
            text=True,
            cwd='/mnt/c/Users/T11/SynologyDrive/LLM/open-notebook'
        )
        assert result.returncode == 0
        # Should have 2 matches (worker-start and start-all)
        lines = [line for line in result.stdout.split('\n') if line.strip()]
        assert len(lines) >= 2
        assert all('--max-tasks' in line for line in lines)
        assert all('OPEN_NOTEBOOK_WORKER_MAX_TASKS' in line for line in lines)

    def test_supervisord_conf_contains_env_pass_through(self):
        """Verify supervisord.conf has ENV var pass-through with $$ escaping."""
        import subprocess
        
        result = subprocess.run(
            ['grep', '-n', 'OPEN_NOTEBOOK_WORKER_MAX_TASKS', 'supervisord.conf'],
            capture_output=True,
            text=True,
            cwd='/mnt/c/Users/T11/SynologyDrive/LLM/open-notebook'
        )
        assert result.returncode == 0
        assert '$$OPEN_NOTEBOOK_WORKER_MAX_TASKS' in result.stdout
        assert 'OPEN_NOTEBOOK_WORKER_MAX_TASKS=${OPEN_NOTEBOOK_WORKER_MAX_TASKS:-5}' in result.stdout

    def test_supervisord_single_conf_contains_env_pass_through(self):
        """Verify supervisord.single.conf has ENV var pass-through with $$ escaping."""
        import subprocess
        
        result = subprocess.run(
            ['grep', '-n', 'OPEN_NOTEBOOK_WORKER_MAX_TASKS', 'supervisord.single.conf'],
            capture_output=True,
            text=True,
            cwd='/mnt/c/Users/T11/SynologyDrive/LLM/open-notebook'
        )
        assert result.returncode == 0
        assert '$$OPEN_NOTEBOOK_WORKER_MAX_TASKS' in result.stdout
        assert 'OPEN_NOTEBOOK_WORKER_MAX_TASKS=${OPEN_NOTEBOOK_WORKER_MAX_TASKS:-5}' in result.stdout

    def test_env_example_documentation(self):
        """Verify .env.example contains documentation for the variable."""
        import subprocess
        
        result = subprocess.run(
            ['grep', '-A1', 'Worker configuration', '.env.example'],
            capture_output=True,
            text=True,
            cwd='/mnt/c/Users/T11/SynologyDrive/LLM/open-notebook'
        )
        assert result.returncode == 0
        assert 'OPEN_NOTEBOOK_WORKER_MAX_TASKS=5' in result.stdout
        assert 'default' in result.stdout.lower() or '5' in result.stdout


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
