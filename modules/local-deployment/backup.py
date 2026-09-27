#!/usr/bin/env python3
"""Archive quiescent local directories using an exported module policy.

Stop writers or use native database export first. Export VM volumes explicitly;
an empty macOS directory is not a backup of a Colima volume.
"""
import argparse
import json
from pathlib import Path
import tarfile


class BackupPolicy:
    def __init__(self, configuration: dict):
        if configuration.get('version') != 2:
            raise ValueError('Export a current module configuration from Settings.')
        if 'local-deployment' not in configuration.get('enabled', []):
            raise ValueError('Local maintenance is disabled in this configuration.')
        self.compression = configuration.get('settings', {}).get('local-deployment', {}).get('compression', 'gzip')
        if self.compression not in ('gzip', 'xz'):
            raise ValueError('Unknown archive compression.')


class BackupJob:
    def __init__(self, policy: BackupPolicy):
        self.policy = policy

    def create(self, destination: Path, directories: list[Path]):
        paths = [p.expanduser().resolve() for p in directories]
        if any(not p.is_dir() or not any(p.iterdir()) for p in paths):
            raise ValueError('Every source must be populated; verify VM paths.')
        if len({p.name for p in paths}) != len(paths):
            raise ValueError('Source directory names must be unique.')
        destination = destination.expanduser().resolve()
        if any(p == destination or p in destination.parents for p in paths):
            raise ValueError('Archive must be outside source directories.')
        with destination.open('xb') as stream:
            destination.chmod(0o600)
            with tarfile.open(fileobj=stream, mode='w:gz' if self.policy.compression == 'gzip' else 'w:xz') as archive:
                for path in paths:
                    archive.add(path, arcname=path.name)
        return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module-state', type=Path, required=True, help='Fresh configuration export; no credentials are included.')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('directories', nargs='+', type=Path)
    args = parser.parse_args()
    try:
        policy = BackupPolicy(json.loads(args.module_state.read_text()))
        result = BackupJob(policy).create(args.output, args.directories)
    except ValueError as error:
        parser.error(str(error))
    print('Private backup created: ' + str(result))
