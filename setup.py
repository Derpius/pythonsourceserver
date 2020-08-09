from setuptools import setup, find_packages

with open("README.md", "r") as readme_file:
    readme = readme_file.read()

requirements = []

setup(
    name="sourceserver",
    version="0.2.0",
    author="100 Pixels Squared",
    author_email="100pxsquared@gmail.com",
    description="Query Source engine servers over UDP",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/100PXSquared/pythonsourceserver/",
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
)