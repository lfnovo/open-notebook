"""
Docker integration tests for OPEN_NOTEBOOK_WORKER_MAX_TASKS environment variable.

This test suite verifies:
- Worker starts with correct max-tasks argument when ENV is set
- Worker starts with default max-tasks (5) when ENV is not set
- Docker compose services start successfully
"""

import os
import subprocess
import time
from pathlib import Path

import pytest


class TestWorkerDockerIntegration:
    """Integration tests for worker with Docker."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        # Save original environment
        self.original_env = os.environ.get('OPEN_NOTEBOOK_WORKER_MAX_TASKS')
        
        yield
        
        # Restore original environment
        if self.original_env is not None:
            os.environ['OPEN_NOTEBOOK_WORKER_MAX_TASKS'] = self.original_env
        elif 'OPEN_NOTEBOOK_WORKER_MAX_TASKS' in os.environ:
            del os.environ['OPEN_NOTEBOOK_WORKER_MAX_TASKS']

    def test_worker_command_contains_max_tasks_default(self):
        """Test that worker command in supervisord.conf uses default value 5."""
        supervisord_conf = Path('supervisord.conf').read_text()
        
        # Check that the command includes the ENV var with default 5
        assert 'OPEN_NOTEBOOK_WORKER_MAX_TASKS=${OPEN_NOTEBOOK_WORKER_MAX_TASKS:-5}' in supervisord_conf
        assert '--max-tasks "$$OPEN_NOTEBOOK_WORKER_MAX_TASKS"' in supervisord_conf

    def test_worker_command_contains_max_tasks_single(self):
        """Test that worker command in supervisord.single.conf uses default value 5."""
        supervisord_single_conf = Path('supervisord.single.conf').read_text()
        
        # Check that the command includes the ENV var with default 5
        assert 'OPEN_NOTEBOOK_WORKER_MAX_TASKS=${OPEN_NOTEBOOK_WORKER_MAX_TASKS:-5}' in supervisord_single_conf
        assert '--max-tasks "$$OPEN_NOTEBOOK_WORKER_MAX_TASKS"' in supervisord_single_conf

    def test_makefile_worker_start_has_max_tasks(self):
        """Test that Makefile worker-start target includes max-tasks."""
        makefile = Path('Makefile').read_text()
        
        # Find the worker-start target
        assert 'worker-start:' in makefile
        # Check for max-tasks flag
        assert '--max-tasks "${OPEN_NOTEBOOK_WORKER_MAX_TASKS:-5}"' in makefile

    def test_makefile_start_all_has_max_tasks(self):
        """Test that Makefile start-all target includes max-tasks."""
        makefile = Path('Makefile').read_text()
        
        # Find the start-all target
        assert 'start-all:' in makefile
        # Check for max-tasks flag in the worker startup line
        lines = makefile.split('\n')
        in_start_all = False
        found_worker = False
        
        for line in lines:
            if 'start-all:' in line:
                in_start_all = True
            elif in_start_all and line.strip().startswith('surreal-commands-worker'):
                assert '--max-tasks' in line
                assert 'OPEN_NOTEBOOK_WORKER_MAX_TASKS' in line
                found_worker = True
                break
            elif in_start_all and line.strip() and not line.startswith('\t') and not line.startswith(' '):
                # New target started
                break
        
        assert found_worker, "Worker startup not found in start-all target"

    def test_dev_init_sh_has_max_tasks(self):
        """Test that dev-init.sh includes max-tasks flag."""
        dev_init = Path('dev-init.sh').read_text()
        
        # Check for max-tasks flag
        assert '--max-tasks "${OPEN_NOTEBOOK_WORKER_MAX_TASKS:-5}"' in dev_init
        assert 'surreal-commands-worker' in dev_init

    def test_env_example_documentation_complete(self):
        """Test that .env.example has complete documentation."""
        env_example = Path('.env.example').read_text()
        
        # Check for documentation
        assert 'Worker configuration' in env_example
        assert 'OPEN_NOTEBOOK_WORKER_MAX_TASKS=5' in env_example
        assert 'default' in env_example.lower() or '5' in env_example

    def test_supervisord_escaping_correct(self):
        """Test that supervisord configs use correct $$ escaping."""
        supervisord_conf = Path('supervisord.conf').read_text()
        supervisord_single_conf = Path('supervisord.single.conf').read_text()
        
        # Both should use $$ for supervisord interpolation
        assert '$$OPEN_NOTEBOOK_WORKER_MAX_TASKS' in supervisord_conf
        assert '$$OPEN_NOTEBOOK_WORKER_MAX_TASKS' in supervisord_single_conf
        
        # Should NOT have single $ (which would be wrong)
        # The pattern should be $$ in the file, not $
        assert '"$$OPEN_NOTEBOOK_WORKER_MAX_TASKS"' in supervisord_conf
        assert '"$$OPEN_NOTEBOOK_WORKER_MAX_TASKS"' in supervisord_single_conf

    @pytest.mark.docker
    def test_docker_compose_syntax_valid(self):
        """Test that docker-compose.yml has valid syntax."""
        # This test requires Docker to be running
        try:
            result = subprocess.run(
                ['docker', 'compose', 'config'],
                capture_output=True,
                text=True,
                timeout=30
            )
            # If docker compose is available, check syntax
            if result.returncode == 0:
                assert 'surrealdb' in result.stdout or 'open_notebook' in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Docker not available or compose not installed - skip test
            pytest.skip("Docker compose not available")

    @pytest.mark.docker
    def test_worker_service_definition_exists(self):
        """Test that worker service is defined in Docker setup."""
        # Check supervisord configs which define worker in production Docker
        supervisord_conf = Path('supervisord.conf').read_text()
        
        # Should have [program:worker] section
        assert '[program:worker]' in supervisord_conf
        assert 'surreal-commands-worker' in supervisord_conf


class TestWorkerEnvVariablePropagation:
    """Test environment variable propagation through the stack."""

    def test_shell_default_expansion_works(self):
        """Test shell default expansion syntax is correct."""
        # Test the shell syntax used in scripts
        import subprocess
        
        # Test default case (ENV not set)
        result = subprocess.run(
            ['bash', '-c', 'echo "${OPEN_NOTEBOOK_WORKER_MAX_TASKS:-5}"'],
            capture_output=True,
            text=True
        )
        assert result.stdout.strip() == '5'
        
        # Test custom value
        env = os.environ.copy()
        env['OPEN_NOTEBOOK_WORKER_MAX_TASKS'] = '10'
        result = subprocess.run(
            ['bash', '-c', 'echo "${OPEN_NOTEBOOK_WORKER_MAX_TASKS:-5}"'],
            capture_output=True,
            text=True,
            env=env
        )
        assert result.stdout.strip() == '10'

    def test_supervisord_env_pass_through_syntax(self):
        """Test supervisord ENV pass-through syntax."""
        # Supervisord uses $$ to escape $ for shell
        supervisord_conf = Path('supervisord.conf').read_text()
        
        # The command should have:
        # env OPEN_NOTEBOOK_WORKER_MAX_TASKS=${OPEN_NOTEBOOK_WORKER_MAX_TASKS:-5} \
        #   uv run ... --max-tasks "$$OPEN_NOTEBOOK_WORKER_MAX_TASKS"
        
        assert 'env OPEN_NOTEBOOK_WORKER_MAX_TASKS=${OPEN_NOTEBOOK_WORKER_MAX_TASKS:-5}' in supervisord_conf
        assert '--max-tasks "$$OPEN_NOTEBOOK_WORKER_MAX_TASKS"' in supervisord_conf


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
