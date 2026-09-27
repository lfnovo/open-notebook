#!/usr/bin/env python3
"""Prepare an isolated, reproducible build with selected optional modules.

The source checkout and existing destination directories are never overwritten.
Usage: python scripts/prepare_modules.py --output /tmp/notebook-build --modules multi-model-research,local-workspace
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def prepare(root: Path, output: Path, selected: list[str], configuration: dict | None = None):
    root, output = root.resolve(), output.resolve()
    if output == root or root in output.parents or output.exists():
        raise ValueError('Choose a new staging directory outside the source checkout.')
    manifests = {p.parent.name: json.loads(p.read_text()) for p in (root/'modules').glob('*/module.json')}
    configuration = configuration or {}
    settings = configuration.get('settings', {})
    if configuration and (configuration.get('version') != 2 or not isinstance(configuration.get('enabled'), list) or not isinstance(settings, dict)):
        raise ValueError('Invalid module configuration export')
    if configuration:
        selected = list(configuration['enabled'])
        bundled = configuration.get('installed', selected)
        if not isinstance(bundled, list) or any(mid not in manifests for mid in bundled):raise ValueError('Invalid installed module inventory')
        selected += [mid for mid in bundled if manifests[mid]['activation'] != 'build' and mid not in selected]
        if any(mid not in manifests for mid in selected) or any(mid not in manifests for mid in settings):
            raise ValueError('Unknown module in configuration')
        for mid in selected:
            if mid in configuration['enabled'] and not set(manifests[mid]['dependencies']) <= set(configuration['enabled']):
                raise ValueError('Disabled dependency in configuration')
    applied_settings = {}
    for mid, manifest in manifests.items():
        fields = {field['key']: field for field in manifest.get('settings', [])}
        values = settings.get(mid, {})
        if not isinstance(values, dict) or set(values) - fields.keys():
            raise ValueError('Unknown module settings: '+mid)
        for key, value in values.items():
            field = fields[key];kind = field['kind']
            valid = (kind == 'boolean' and type(value) is bool
                or kind == 'integer' and type(value) is int and field.get('minimum', value) <= value <= field.get('maximum', value)
                or kind == 'choice' and isinstance(value, str) and value in field['options']
                or kind == 'text' and isinstance(value, str) and 1 <= len(value.strip()) <= 120)
            if not valid:raise ValueError('Invalid module setting: '+mid+'.'+key)
        applied_settings[mid] = {**{key: field['default'] for key, field in fields.items()}, **values}
    ordered, visiting = [], set()
    def visit(mid):
        if mid in ordered:
            return
        if mid not in manifests or mid in visiting:
            raise ValueError('Unknown module or dependency cycle: '+mid)
        visiting.add(mid)
        for dep in manifests[mid]['dependencies']:
            visit(dep)
        visiting.remove(mid)
        ordered.append(mid)
    for mid in selected:
        visit(mid)
    # Validate every overlay before creating a staging directory. Upstream drift
    # must be reviewed, never silently overwritten by a local customization.
    targets = set()
    for mid in ordered:
        index = root/'modules'/mid/'overlay.json'
        for patch in json.loads(index.read_text()) if index.exists() else []:
            relative = Path(patch['target'])
            if relative.is_absolute() or '..' in relative.parts or str(relative) in targets:
                raise ValueError('Unsafe or conflicting overlay: '+str(relative))
            targets.add(str(relative))
            original = root/relative
            digest = hashlib.sha256(original.read_bytes()).hexdigest() if original.exists() else None
            if digest != patch['sha256_before']:
                raise ValueError('Upstream file changed; rebase the module overlay: '+str(relative))
    files = subprocess.check_output(['git','ls-files','-c','-o','--exclude-standard','-z'],cwd=root).decode().split('\0')
    output.mkdir(parents=True)
    for name in dict.fromkeys(files):
        if not name:
            continue
        source = root/name
        if source.is_symlink():
            raise ValueError('Source symlinks are not allowed in module builds: '+name)
        if source.is_file():
            dest = output/name
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,dest)
    imports, entries = ["import dynamic from 'next/dynamic'"], []
    for number, mid in enumerate(ordered):
        module = root/'modules'/mid
        index = module/'overlay.json'
        for patch in json.loads(index.read_text()) if index.exists() else []:
            dest = output/patch['target']
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(module/'overlay'/patch['target'],dest)
        spec = manifests[mid].get('frontend')
        if not spec:
            continue
        shutil.copytree(module/'frontend',output/'frontend/src/modules'/mid)
        imports.append(f"const Page{number} = dynamic(() => import( '@/modules/{mid}/{spec['entry'].removesuffix('.tsx')}'))")
        widget = ''
        if spec.get('search_widget'):
            imports.append(f"const Widget{number} = dynamic(() => import('@/modules/{mid}/{spec['search_widget'].removesuffix('.tsx')}'))")
            widget = f'SearchWidget: Widget{number}, '
        if (module/'frontend/locales.ts').exists():
            imports.append(f"import {{ moduleLocales as locales{number} }} from '@/modules/{mid}/locales'")
            entries.append(f"  '{mid}': {{ {widget}Page: Page{number}, locales: locales{number} }},")
        else:
            entries.append(f"  '{mid}': {{ {widget}Page: Page{number} }},")
        route = spec['route'].strip('/')
        if not route or '..' in Path(route).parts:
            raise ValueError('Invalid frontend route')
        alias = output/'frontend/src/app/(dashboard)'/route/'page.tsx'
        if alias.exists():
            raise ValueError('Module route conflicts with a core route: '+route)
        alias.parent.mkdir(parents=True,exist_ok=True)
        alias.write_text("import { ModulePage } from '@/components/modules/ModulePage'\nexport default function Page() { return <ModulePage id="+json.dumps(mid)+" /> }\n")
    # Legacy build adapters are applied only in this isolated staging tree.
    # These transformations are deterministic and never edit the source checkout.
    if 'local-processing' in ordered:
        values = applied_settings['local-processing']
        path = output/'open_notebook/graphs/source.py'
        if not values.get('prefer_turkish', True):
            path.write_text(path.read_text().replace('YOUTUBE_PREFERRED_LANGUAGES = [\n    "tr",', 'YOUTUBE_PREFERRED_LANGUAGES = [', 1))
    if 'local-workspace' in ordered and applied_settings['local-workspace'].get('density') == 'compact':
        path = output/'frontend/src/app/globals.css'
        path.write_text(path.read_text() + '\n/* Module-owned compact density. */\n:root { --spacing: 0.225rem; }\n')
    generated = output/'frontend/src/lib/modules/generated.ts'
    generated.write_text("// Generated by scripts/prepare_modules.py; edit module sources instead.\nimport type { ModuleEntry } from './types'\n"+'\n'.join(imports)+"\nexport const moduleEntries: Record<string, ModuleEntry> = {\n"+'\n'.join(entries)+"\n}\n")
    if configuration:
        (output/'modules/defaults.json').write_text(json.dumps({key:configuration[key] for key in ('version','revision','enabled','settings')},indent=2)+'\n')
    (output/'modules/installed.json').write_text(json.dumps(ordered,indent=2)+'\n')
    (output/'modules/build.json').write_text(json.dumps({'schema_version':1,'modules':ordered,'overlay_targets':sorted(targets),'settings':{mid:applied_settings[mid] for mid in ordered}},indent=2)+'\n')
    return ordered


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--modules',default='')
    parser.add_argument('--state',type=Path,help='Configuration exported from Settings → Modules settings')
    args=parser.parse_args()
    if args.state and args.modules:parser.error('Use --state or --modules, not both')
    installed=prepare(Path(__file__).resolve().parents[1],args.output,[x.strip() for x in args.modules.split(',') if x.strip()],json.loads(args.state.read_text()) if args.state else None)
    print('Prepared modules: '+(', '.join(installed) or '(core only)'))
    print('Build directory: '+str(args.output.resolve()))
