#!/usr/local/python3
"""Bundle being source as tar and bundle it together with an install bash script
inside a zip.

Resources:
  https://unix.stackexchange.com/questions/90191/how-to-extract-archive-via-network
"""
import argparse
import contextlib
import glob
import io
import os
import sys
import tarfile
import zipfile


NODE_IDS = {
    0: [1, 2],
    1: [3, 4],
    2: [5, 6],
    3: [7, 8],
    4: [9, 10],
    #5: [11, 12],
    5: [20, 21],
    6: [13, 14],
    7: [15, 16],
    8: [17, 18],
    #9: [19, 20],
    #10: [21, 22],
    11: [13, 24],
    12: [25, 26],
    13: [27, 28],
    14: [29, 30],
    15: [31, 32],
    16: [33, 34],
    17: [35, 36],
}
"""ECAL being id -> node ids."""


BEING_INI = """[Logging]
DIRECTORY = log
"""
"""Default Being ini config file."""


INSTALL_SCRIPT_TEMPLATE = '''#!/bin/bash
if ! ping -c 1 -W 1 "{hostname}.local";
then
  echo "Kit {hostname} not reachable :(";
  exit -1;
fi
cd "`dirname "$0"`"
echo "Uploading source code to kit {hostname}";
echo {tarname};
cat "{tarname}" | ssh "pi@{hostname}.local" "tar zxvf -";
echo "Restarting being.service";
ssh "pi@{hostname}.local" "sudo systemctl restart being.service";
echo "Done with updating the software. You can close now this windows.";
'''

TMP_SCRIPT = 'tmp script.sh'
"""Tmp script filename for making it executable."""


def cli() -> argparse.Namespace:
    """Command line interface."""
    parser = argparse.ArgumentParser()
    parser.add_argument('id', help='ECAL being kit id', type=int)
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    return parser.parse_args()


def remove_py_cache(directory: str):
    """Remove all Python cache files and __pycache__ directories at
    directory.

    Args:
        directory: Directory to recursively purge from Python cache files /
            directories.
    """
    cmd = f'find "{directory}" | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf'
    return os.system(cmd)


def format_ecal_program(id: int) -> str:
    """Format ECAL Being program for a given kit id.

    Args:
        id: ECAL Being kit number.

    Returns:
        str: Formatted Python program string.
    """
    with open('ecal_being.py') as f:
        data = f.read()

    lines = data.split('\n')
    for nr, line in enumerate(lines):
        if line.startswith('NODE_IDS'):
            break
    else:
        raise RuntimeError("Could not find NODE_IDS line in 'ecal_being.py'")

    lines[nr] = f'NODE_IDS = {NODE_IDS[id]}'
    ecalProgram = '\n'.join(lines)
    return ecalProgram


def write_string(tarh, data, arcname):
    """Write string to tar file handler.

    Args:
        tarh: TAR file handler.
        data: String to write.
        arcname: Target filepath in TAR file???
    """
    tarinfo = tarfile.TarInfo(arcname)
    tarinfo.size = len(data)
    tarh.addfile(tarinfo, io.BytesIO(data.encode()))


if __name__ == '__main__':
    args = cli()
    hostname = f'ecal-being-{args.id}'
    print(f'hostname: {hostname!r}')

    sys.path.append(os.getcwd())
    from being import __version__
    print('Being version:', __version__)
    zipname = f'{hostname} {__version__}.zip'
    tarname = f'{hostname} {__version__}.tar.gz'

    # Being source files
    sourcedir = 'being'
    remove_py_cache(sourcedir)
    sourcefiles = glob.glob(sourcedir + '/**/*', recursive=True)
    assert bool(sourcefiles), f'Did not find being source files in {sourcedir!r}!'
    print(f'Found {len(sourcefiles)} source files in {sourcedir!r}')

    # ECAL program
    print(f'Formatting ecal_being.py program for kit {args.id}')
    ecalProgram = format_ecal_program(args.id)

    with contextlib.ExitStack() as stack:
        # Bash install script
        print(f'Formatting install.sh script for {hostname!r}')
        installScript = INSTALL_SCRIPT_TEMPLATE.format(
            hostname=hostname,
            tarname=tarname,
        )

        if os.path.exists(TMP_SCRIPT):
            os.chmod(TMP_SCRIPT, 0o777)
            os.remove(TMP_SCRIPT)

        with open(TMP_SCRIPT, 'w') as f:
            f.write(installScript)

        #os.chmod(TMP_SCRIPT, 0o700)
        os.chmod(TMP_SCRIPT, 0o500)
        stack.callback(lambda: os.remove(TMP_SCRIPT))

        with tarfile.open(tarname, 'w:gz') as tarh:
            if args.verbose:
                print(f'Creating {tarname!r} (tmp file)')
                print('Packing source files ')

            for fp in sourcefiles:
                dst = os.path.join('being', fp)
                if args.verbose:
                    print(f'Adding {dst!r}')

                tarh.add(fp, dst)

            if args.verbose:
                print("Creating 'ecal_being.py'")

            write_string(tarh, ecalProgram, 'ecal_being.py')

            if args.verbose:
                print("Creating 'being.ini'")

            write_string(tarh, BEING_INI, 'being.ini')

        stack.callback(lambda: os.remove(tarname))

        with zipfile.ZipFile(zipname, 'w') as ziph:
            if args.verbose:
                print(f'Creating {zipname!r}')
                print(f'Moving {tarname!r} -> {zipname!r}')

            ziph.write(tarname)

            if args.verbose:
                print('Packing install.sh')

            ziph.write(TMP_SCRIPT, arcname='install.command')

        print(f'Successfully bundled {zipname!r}')
