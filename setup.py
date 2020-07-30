"""setup.py file."""

import uuid

from setuptools import setup, find_packages
try:
    # pip >=20
    from pip._internal.network.session import PipSession
    from pip._internal.req import parse_requirements
except ImportError:
    try:
        # 10.0.0 <= pip <= 19.3.1
        from pip._internal.download import PipSession
        from pip._internal.req import parse_requirements
    except ImportError:
        # pip <= 9.0.3
        from pip.download import PipSession
        from pip.req import parse_requirements

__author__ = 'Yann Masson <yann.masson@orange.fr>'

install_reqs = parse_requirements('requirements.txt', session=uuid.uuid1())
reqs = [str(ir.req) for ir in install_reqs]

setup(
    name="napalm-hios",
    version="0.1.0",
    packages=find_packages(),
    author="Yann Masson",
    author_email="yann.masson@orange.fr",
    description="Network Automation and Programmability Abstraction Layer Hirschmann HiOS",
    long_description="Hirschmann HiOS driver support for Napalm network automation
    classifiers=[
        'Topic :: Utilities',
         'Programming Language :: Python',
         'Programming Language :: Python :: 3',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',
    ],
    url="https://github.com/napalm-automation/napalm-hios",
    include_package_data=True,
    install_requires=reqs,
)
