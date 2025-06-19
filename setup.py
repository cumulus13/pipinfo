from setuptools import setup, find_packages
from pathlib import Path
import shutil

NAME = 'pypi_info'
shutil.copy('__version__.py', str(Path(NAME) / '__version__.py'))

def get_version():
    try:
        with open(f"{NAME.replace('-', '_')}/__version__.py", "r") as f:
             for line in f:
                 if line.strip().startswith("version"):
                     parts = line.split("=")
                     if len(parts) == 2:
                         return parts[1].strip().strip('"').strip("'")
    except Exception as e:
        print(f"Error getting version: {e}")
    return "0.1"

def requirements():
    try:
        with open('requirements.txt', 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading requirements: {e}")
    return []

setup(
    name=NAME,
    version=get_version(),
    # packages=find_packages(exclude=["*.pipinfo1.py"]),
    packages=[NAME.replace("-","_")],
    include_package_data=True,
    # package_data={
    #     'pipinfo': ['batmaker.ini'],
    # },
    install_requires=requirements(),
    entry_points={
        'console_scripts': [
            'pipinfo = pypi_info.pipinfo:main',
            'pypi-info = pypi_info.pipinfo:main',
            'pypi_info = pypi_info.pipinfo:main',
        ],
    },
    author="Hadi Cahyadi",
    author_email="cumulus13@gmail.com",
    description="Search and get description of package on pypi.org",
    long_description=(Path(__file__).parent / "README.md").read_text(encoding="utf-8") if Path("README.md").exists() else "",
    long_description_content_type="text/markdown",
    url="https://github.com/cumulus13/pipinfo",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
    ],
    python_requires='>=3.7',
    license="MIT",
)
