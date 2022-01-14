import pathlib
from setuptools import setup, find_packages

# The directory containing this file
HERE = pathlib.Path(__file__).parent

README = (HERE / "README.md").read_text()
INSTALL_REQUIRED = (HERE / "requirements.txt").read_text()
IMAGE_EXTRA_REQUIRED = (HERE / "image_extra_requirements.txt").read_text()
SETUP_REQUIRED = (HERE / "setup_requirements.txt").read_text()
TEST_REQUIRED = (HERE / "test_requirements.txt").read_text()

setup(
    name='weconnect',
    packages=find_packages(),
    version=open("weconnect/__version.py").readlines()[-1].split()[-1].strip("\"'"),
    description='Python API for the Volkswagen WeConnect Services',
    long_description=README,
    long_description_content_type="text/markdown",
    author='Till Steinbach',
    keywords='weconnect, we connect, carnet, car net, volkswagen, vw, telemetry',
    url='https://github.com/tillsteinbach/WeConnect-python',
    project_urls={
        'Funding': 'https://github.com/sponsors/tillsteinbach',
        'Source': 'https://github.com/tillsteinbach/WeConnect-python',
        'Bug Tracker': 'https://github.com/tillsteinbach/WeConnect-python/issues'
    },
    license='MIT',
    install_requires=INSTALL_REQUIRED,
    extras_require={
        "Images": IMAGE_EXTRA_REQUIRED,
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Libraries',
    ],
    python_requires='>=3.7',
    setup_requires=SETUP_REQUIRED,
    tests_require=TEST_REQUIRED,
    include_package_data=True,
    zip_safe=False,
)
