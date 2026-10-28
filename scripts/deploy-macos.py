"""Deploy a trusted PC/CI-built static archive to a per-user macOS Caddy service."""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.parse import urlsplit


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--bind', required=True, help='Private LAN IPv4 address')
    parser.add_argument('--port', type=int, default=8086)
    parser.add_argument('--site-url', required=True, help='Must match the built SITE_URL')
    parser.add_argument('--home', type=Path, default=Path.home() / 'Services/openjlpt')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        raise ValueError('This deployer requires macOS')
    address = ipaddress.ip_address(args.bind)
    if address.version != 4 or not address.is_private or address.is_loopback:
        raise ValueError('--bind must be a private LAN IPv4 address')
    if not 1024 <= args.port <= 65535:
        raise ValueError('Use an unprivileged port from 1024 to 65535')
    url = urlsplit(args.site_url)
    if url.scheme != 'http' or url.hostname != args.bind or url.port != args.port or url.path not in ('', '/'):
        raise ValueError('--site-url must match http://LAN-IP:PORT/')
    caddy = shutil.which('caddy')
    if not caddy:
        raise ValueError('Install Caddy and add its directory to PATH')
    repo = Path(__file__).resolve().parents[1]
    revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    if subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'], text=True).strip():
        raise ValueError('Deploy from a clean GitHub checkout')
    home = args.home.resolve()
    releases = home / 'releases'
    releases.mkdir(parents=True, exist_ok=True)
    release = Path(tempfile.mkdtemp(prefix=revision[:12] + '-', dir=releases))
    with tarfile.open(args.archive) as archive:
        for member in archive.getmembers():
            target = (release / member.name).resolve()
            if not target.is_relative_to(release) or not (member.isfile() or member.isdir()):
                raise ValueError('Archive contains an unsafe entry: ' + member.name)
        archive.extractall(release)
    built = json.loads((release / 'deployment.json').read_text(encoding='utf-8-sig'))
    if built != {'revision': revision, 'site_url': args.site_url.rstrip('/') + '/'}:
        raise ValueError('Archive revision or SITE_URL does not match the deployment')
    for name in ('index.html', 'data.html', 'downloads/openjlpt-data.zip', 'dataset/openjlpt.sqlite'):
        if not (release / name).is_file():
            raise ValueError('Missing build output: ' + name)
    config = home / 'Caddyfile'
    current = home / 'current'
    config.write_text(
        '{\n    admin off\n    auto_https off\n}\n'
        f'http://:{args.port} {{\n'
        f'    bind {args.bind} 127.0.0.1\n'
        f'    root * "{current}"\n'
        '    encode zstd gzip\n'
        '    file_server\n'
        '}\n', encoding='utf-8')
    run(caddy, 'validate', '--config', str(config), '--adapter', 'caddyfile')
    if current.exists() and not current.is_symlink():
        raise ValueError('Refusing to replace a non-symlink current directory')
    if current.is_symlink():
        previous = home / 'previous.next'
        previous.symlink_to(current.resolve(), target_is_directory=True)
        previous.replace(home / 'previous')
    link = home / 'current.next'
    link.symlink_to(release, target_is_directory=True)
    link.replace(current)
    label = 'io.openjlpt.lan'
    logs = home / 'logs'
    logs.mkdir(exist_ok=True)
    plist = Path.home() / 'Library/LaunchAgents' / f'{label}.plist'
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_bytes(plistlib.dumps({
        'Label': label,
        'ProgramArguments': [caddy, 'run', '--config', str(config), '--adapter', 'caddyfile'],
        'RunAtLoad': True, 'KeepAlive': True, 'ThrottleInterval': 10,
        'WorkingDirectory': str(home),
        'StandardOutPath': str(logs / 'stdout.log'),
        'StandardErrorPath': str(logs / 'stderr.log'),
    }))
    domain = f'gui/{os.getuid()}'
    existing = subprocess.run(['launchctl', 'print', f'{domain}/{label}'], capture_output=True)
    if existing.returncode == 0:
        run('launchctl', 'bootout', f'{domain}/{label}')
    run('launchctl', 'bootstrap', domain, str(plist))
    print(json.dumps({'ok': True, 'revision': revision, 'release': str(release), 'url': args.site_url}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'ok': False, 'stage': 'deploy', 'message': str(error)}), file=sys.stderr)
        sys.exit(1)
