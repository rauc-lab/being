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
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: MacOS X',
        'Environment :: Other Environment',
        'Environment :: Web Environment',
        'Framework :: Robot Framework',
        'Framework :: Robot Framework :: Library',
        'Framework :: Robot Framework :: Tool',
        'Framework :: Sphinx',
        'Framework :: aiohttp',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Other Audience',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: OS Independent',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Operating System :: POSIX :: Other',
        'Operating System :: Unix',
        'Programming Language :: JavaScript',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Artistic Software',
        'Topic :: Communications',
        'Topic :: Education',
        'Topic :: Games/Entertainment',
        'Topic :: Home Automation',
        'Topic :: Multimedia',
        'Topic :: Multimedia :: Graphics',
        'Topic :: Multimedia :: Graphics :: Editors',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Sound/Audio :: Analysis',
        'Topic :: Multimedia :: Sound/Audio :: Capture/Recording',
        'Topic :: Other/Nonlisted Topic',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Human Machine Interfaces',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: Software Development :: Widget Sets',
        'Topic :: System',
        'Topic :: System :: Hardware',
        'Topic :: System :: Networking',
        'Topic :: Utilities',
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
        'jinja2>=3.0.0',
        'aiohttp-jinja2',
        'ruamel.yaml',
        'tomlkit',
        'configobj',
    ],
    extras_require = {
        # portaudio needs to be installed
        'audio':  ['PyAudio'],

        # Needed on Rpi for accessing GPIO.
        'rpi':  ['RPi.GPIO'],
    },
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
    project_urls={
        'Documentation': 'https://being.readthedocs.io/en/latest/',
        'PyPi': 'https://pypi.org/project/being/',
        'Source': 'https://github.com/rauc-lab/being',
        'Tracker': 'https://github.com/rauc-lab/being/issues',
        'RAUC': 'https://asl.ethz.ch/research/rauc.html',
    },
    license_files = ('LICENSE',),
    url='https://github.com/rauc-lab/being',
    platforms=['Darwin', 'Linux'],
    license='MIT',
)
