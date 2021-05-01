import collections
import datetime
import os
import re
import subprocess
import sys
import time
from subprocess import TimeoutExpired, CalledProcessError

import being


KIT_NUMBERS = [0]
MOTOR_IDS = collections.defaultdict(lambda: [1, 2], {
    0: [1, 2],
    1: [3, 4],
    2: [5, 6],
    3: [7, 8],
    4: [9, 10],
    5: [11, 12],
    6: [13, 14],
    7: [15, 16],
    8: [17, 18],
    9: [19, 20],
    10: [21, 22],
    11: [23, 24],
})
HOSTNAME = 'ecal-being-{}.local'
SUCCESS = 0
UNTITLED_MOTION = """{"type": "BPoly", "extrapolate": false, "axis": 0, "knots": [0.0, 2.0, 4.0, 6.0, 8.0], "coefficients": [[[0.0, 0.0], [0.1, 0.0], [0.1, 0.1], [0.0, 0.1]], [[0.0, 0.0], [0.1, 0.0], [0.1, 0.1], [0.0, 0.1]], [[0.1, 0.0], [0.1, 0.1], [0.0, 0.1], [0.0, 0.0]], [[0.1, 0.0], [0.1, 0.1], [0.0, 0.1], [0.0, 0.0]]]}
"""
DEFAULT_BEHAVIOR = """{
    "attentionSpan": 0,
    "motions": [
        [
            "Untitled"
        ],
        [],
        []
    ]
}
"""
DEFAULT_BEING_INI = """[Logging]
DIRECTORY=log
"""
BEING_SERVICE = 'being.service'


def format_timestamp(seconds):
    parts = []
    for div in [3600, 60, 1]:
        a, seconds = divmod(seconds, div)
        parts.append('%02d' % a)

    return ':'.join(parts)


def iter_with_progress_bar(stuff, length=None, prefix='', width=40, stream=sys.stdout):
    """Iterate over stuff while a printing progress bar.

    Args:
        stuff: Stuff it iterate over.

    Kwargs:
        length: Length of iterable.
        prefix:
        width: Progress bar character width.
        stream: Output stream.
    """
    if length is None:
        length = len(stuff)

    startTime = time.perf_counter()
    for i, thing in enumerate(stuff):
        progress = max(0., min(1., (i / (length - 1))))

        # Render bar
        ticks = int(progress * width)
        bar = '[%s%s]' % (ticks * '*', (width - ticks) * ' ')

        # ETA / remaining time
        now = time.perf_counter()
        if progress == 0:
            eta = float('inf')
        else:
            passed = now - startTime
            eta = startTime + passed / progress

        remaining = eta - now

        # Print
        stream.write('\33[2K\r')
        stream.write(' '.join([prefix, bar, '%.1f sec' % remaining]))
        stream.flush()

        yield thing

    stream.write('\n')
    stream.flush()


def format_ecal_program(motorIds: list) -> str:
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
        raise RuntimeError("Could not find MOTOR_IDS line in 'ecal_being.py'")

    lines[nr] = f'NODE_IDS = {motorIds}'
    ecalProgram = '\n'.join(lines)
    return ecalProgram


def is_ssh_destination(string) -> bool:
    """Check if string is a (more or less) valid SSH address (user@host:...)."""
    return bool(re.match(r'([^\s]+)@([^\s]+):(.*)', string))


def validate_ssh_destination(string):
    """Validate SSH address and raise ValueError."""
    if not is_ssh_destination(string):
        raise ValueError(f'{string!r} is not a valid SSH destination!')


def run_cmd(cmd, *args, **kwargs) -> object:
    """Run subprocess command."""
    return subprocess.run(cmd, stdout=subprocess.DEVNULL, check=True)


def copy_file(src, dst):
    assert os.path.isfile(src)
    validate_ssh_destination(dst)
    address, filepath = dst.split(':')
    run_cmd(['ssh', address, 'mkdir', '-p', os.path.dirname(filepath)])
    run_cmd(['scp', src, dst])


def copy_directory(src, dst):
    assert os.path.isdir(src)
    validate_ssh_destination(dst)
    address, filepath = dst.split(':')
    run_cmd(['ssh', address, 'mkdir', '-p', os.path.dirname(filepath)])
    run_cmd(['scp', '-r', src, dst])


def write_file_to_remote(data, dst):
    """Write data to remote file."""
    validate_ssh_destination(dst)
    address, filepath = dst.split(':')
    directory, filename = os.path.split(filepath)
    run_cmd(['ssh', address, f'mkdir -p {directory}'])
    proc = subprocess.Popen(['ssh', address, f'cat > {filepath}'], stdin=subprocess.PIPE)
    outs, errs = proc.communicate(input=data.encode())
    if errs:
        raise RuntimeError(errs)


def copy_stuff(src, dst):
    if os.path.exists(src):
        if os.path.isdir(src):
            copy_directory(src, dst)
        else:
            copy_file(src, dst)
    else:
        write_file_to_remote(src, dst)


def remove_remote_directory(dst):
    validate_ssh_destination(dst)
    address, filepath = dst.split(':')
    run_cmd(['ssh', address, 'rm', '-r', filepath])


def read_remote_file(dst):
    address, filepath = dst.split(':')
    proc = subprocess.Popen(
        ['ssh', address, 'cat', filepath],
        stdout=subprocess.PIPE,
    )
    data = proc.stdout.read()
    return data.decode()


def ping(hostname, timeout=.5) -> bool:
    """Ping hostname and return if reachable."""
    try:
        ret = run_cmd(
            ['ping', '-c', '1', hostname],
            timeout=timeout,
        )
        return (ret.returncode == SUCCESS)
    except (TimeoutExpired, CalledProcessError):
        return False


def being_service(address, command):
    run_cmd(['ssh', address, 'sudo', 'systemctl', command, BEING_SERVICE])


def read_remote_being_version(address, timeout=2.):
    proc = subprocess.Popen(
        ['ssh', address, 'python3', '-'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )

    getVersionProgramm = b"""import sys
import being
print(being.__version__)
sys.exit(0)
"""
    try:
        outs, errs = proc.communicate(getVersionProgramm, timeout)
        return outs.decode().strip()
    except TimeoutExpired:
        proc.kill()
        outs, errs = proc.communicate()
        return ''


def update_remote_clock(address):
    # Note: This is not persistent since the RPi has not battery. But still
    # useful to not have time mismatches and skipped updates...
    now = datetime.datetime.now()
    run_cmd([
        'ssh',
        address,
        f'sudo date --set="{now.isoformat()}"',
    ])


def setup_being(nr, verbose=True, motion=True, indent=''):
    hostname = HOSTNAME.format(nr)
    reachable = ping(hostname)
    address = 'pi@' + hostname
    program = format_ecal_program(MOTOR_IDS[nr])

    if verbose: print(indent + 'Updating clock')
    update_remote_clock(address)

    try:
        remove_remote_directory(address + ':~/being')
    except CalledProcessError:
        pass

    STUFF = [
        ('being', address + ':~/being/being'),
        ('setup.py', address + ':~/being/setup.py'),
        (UNTITLED_MOTION, address + ':~/content/Untitled.json'),
        (DEFAULT_BEHAVIOR, address + ':~/behavior.json'),
        (DEFAULT_BEING_INI, address + ':~/being.ini'),
        (program, address + ':~/ecal_being.py'),
    ]
    for src, dst in iter_with_progress_bar(STUFF, prefix=indent + 'Copying files'):
        copy_stuff(src, dst)

    print(indent + 'Validate')
    remoteProgram = read_remote_file(address + ':~/ecal_being.py')
    print(indent + '- ecal_being.py:        ', program.strip() == remoteProgram.strip())
    ver = read_remote_being_version(address)
    print(indent + '- Correct being version:', being.__version__ == ver)
    if motion:
        m = read_remote_file(address + ':~/content/Untitled.json')
        print(indent + '- Untitled.json:        ', m == UNTITLED_MOTION)

    print(indent + 'Restarting ' + BEING_SERVICE)
    being_service(address, 'restart')


for nr in KIT_NUMBERS:
    hostname = HOSTNAME.format(nr)
    print(hostname)
    reachable = ping(hostname)
    if not reachable:
        print('  NOT REACHABLE')
        continue

    setup_being(nr, indent='  ')
