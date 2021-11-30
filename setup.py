"""
Possible resoruces:
  - https://packaging.python.org/guides/distributing-packages-using-setuptools/
"""
import glob

from setuptools import setup, find_packages

import being


with open('README.rst') as file:
    longDescription = file.read()


setup(
    author='Alexander Theler',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Console',
        'Environment :: MacOS X',
        'Environment :: Other Environment',
        'Framework :: Robot Framework',
        'Framework :: Robot Framework :: Library',
        'Framework :: Robot Framework :: Tool',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Other Audience',
        'Intended Audience :: Science/Research',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Artistic Software',
        'Topic :: Education',
        'Topic :: Games/Entertainment',
        'Topic :: Multimedia',
        'Topic :: Other/Nonlisted Topic',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Human Machine Interfaces',
        'Topic :: System :: Hardware',
        'Topic :: System :: Hardware :: Hardware Drivers',
    ],
    description='Robotic core for the PATHOS project.',
    install_requires=[
        'setuptools',
        'numpy',
        'scipy',
        'matplotlib',
        'python-can',
        'canopen',
        'aiohttp >= 3.7.0, <= 3.7.4',  # 4.0.0 leads to problems (weakref on WebSocketResponse)
        'aiohttp-jinja2',
        #'RPi.GPIO',  # Needed on Rpi. We do not include it here that being can run on normal computers...
        #'PyAudio',  # Optional. Not needed right now
        'ruamel.yaml',
        'tomlkit',
        'configobj',
    ],
    keywords='Poetic animatronics robotic framework',
    long_description=longDescription,
    name='being',
    packages=find_packages(),
    data_files=[
        ('scripts', glob.glob('scripts/*.py')),
    ],
    include_package_data=True,
    test_suite='tests',
    version=being.__version__,
    #project_urls={}  # TODO(atheler)
)
