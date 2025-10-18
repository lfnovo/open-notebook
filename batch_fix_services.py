#!/usr/bin/env python3
"""Batch fix service files for mypy errors."""
import re
from pathlib import Path

SERVICE_FILES = [
    'api/notes_service.py',
    'api/insights_service.py',
    'api/episode_profiles_service.py',
    'api/settings_service.py',
    'api/sources_service.py',
    'api/podcast_service.py',
    'api/command_service.py',
]

BASE_DIR = Path('/Users/luisnovo/dev/projetos/open-notebook/open-notebook')

for service_file in SERVICE_FILES:
    file_path = BASE_DIR / service_file
    if not file_path.exists():
        print(f"Skipping {service_file} - file not found")
        continue

    content = file_path.read_text()
    original_content = content

    # Pattern to find: var_name = api_client.method(args)
    # Followed by: var_name["key"] or var_name.get("key")
    lines = content.split('\n')
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this line has an api_client call assignment
        match = re.match(r'(\s*)(\w+)\s*=\s*api_client\.(\w+)\((.*)\)\s*$', line)
        if match and 'response = api_client' not in line:
            indent = match.group(1)
            var_name = match.group(2)
            method_name = match.group(3)
            args = match.group(4)

            # Look ahead to see if this variable is used with dict access
            has_dict_access = False
            for j in range(i+1, min(i+15, len(lines))):
                next_line = lines[j]
                if f'{var_name}["' in next_line or f"{var_name}['" in next_line or f'{var_name}.get(' in next_line:
                    has_dict_access = True
                    break
                # Stop looking if we hit a blank line, new function, or new assignment
                if (not next_line.strip() or
                    next_line.strip().startswith('def ') or
                    next_line.strip().startswith('class ') or
                    (re.match(r'\s*\w+\s*=', next_line) and var_name not in next_line)):
                    break

            if has_dict_access:
                # Replace with response and isinstance check
                new_lines.append(f'{indent}response = api_client.{method_name}({args})')
                new_lines.append(f'{indent}{var_name} = response if isinstance(response, dict) else response[0]')
                i += 1
                continue

        new_lines.append(line)
        i += 1

    new_content = '\n'.join(new_lines)

    # Check if content changed
    if new_content != original_content:
        file_path.write_text(new_content)
        print(f"✓ Fixed {service_file}")
    else:
        print(f"- No changes needed for {service_file}")

print("\nDone!")
