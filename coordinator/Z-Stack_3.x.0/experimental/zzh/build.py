#!/usr/bin/env python3
"""Rebuild the configured experimental CC2652R project; see README.md for setup."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
TARGET = 'znp_CC26X2R1_LAUNCHXL_tirtos7_ticlang'
NAME = 'CC2652R_coordinator_20250321_sdk8.33.00.16'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--ccs', type=Path, required=True, help='CCS 21.0.1 installation root')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sdk, ccs, output = (p.resolve() for p in (args.sdk, args.ccs, args.output))
    project = sdk / 'workspace' / TARGET
    config = (project / '.cproject').read_text()
    for expected in ['SDK:8.33.0.16;', 'sysconfig:1.28.2;', 'TICLANG_5.1.1.LTS']:
        if expected not in config:
            raise RuntimeError(f'Project does not select {expected}; follow README.md')
    # Detect unapplied patches or unexpected SDK/source changes before building.
    for name, expected in json.loads((HERE / 'patched-source-sha256.json').read_text()).items():
        actual = hashlib.sha256((sdk / name).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f'Source mismatch: {name}; review before rebuilding')
    for assignment in ['device.enableDCDC = false;', 'NVS1.internalFlash.regionBase = 0x50000;',
                       'NVS1.internalFlash.regionSize = 0x6000;', 'zstack.rf.txPower = "5";']:
        if assignment not in (project / 'znp.syscfg').read_text():
            raise RuntimeError(f'Missing zzh setting: {assignment}')
    output.mkdir(parents=True, exist_ok=True)
    cli = ccs / 'ccs/eclipse/ccs-server-cli.sh'
    with (output / 'build.log').open('w') as log:
        subprocess.run([str(cli), '-workspace', str(sdk / 'workspace'), '-application',
                        'buildProject', '-ccs.projects', TARGET, '-ccs.configuration', 'default'],
                       cwd=sdk, stdout=log, stderr=subprocess.STDOUT, check=True)
    log = (output / 'build.log').read_text()
    if '0 out of 1 projects have errors' not in log:
        raise RuntimeError(f'CCS did not report a successful build; inspect {output / "build.log"}')
    subprocess.run([sys.executable, 'package.py'], cwd=sdk, check=True)
    with zipfile.ZipFile(sdk / 'dist/CC2652R_coordinator_20250321.zip') as archive:
        data = archive.read('CC2652R_coordinator_20250321.hex')
    image, archive_path = output / (NAME + '.hex'), output / (NAME + '.zip')
    image.write_bytes(data)
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(NAME + '.hex', data)
    check = subprocess.run([sys.executable, str(HERE / 'validate_firmware.py'), str(image),
                            str(archive_path)], text=True, capture_output=True, check=True)
    (output / 'validation.json').write_text(check.stdout)
    shutil.copy2(HERE / 'build-manifest.json', output / 'build-manifest.json')
    print(check.stdout, end='')
    print(f'Firmware: {archive_path}')


if __name__ == '__main__':
    main()
