from setuptools import setup

setup(
    name="simple_extract",
    version="0.1.0",
    packages=[""],
    url="https://github.com/berrym/simple-extract.git",
    license="MIT",
    author="Michael Berry",
    author_email="trismegustis@gmail.com",
    description="A small command line utility to help extract compressed archives",
    entry_points={
        "console_scripts": [
            "simple-extract = simple_extract:main",
        ],
    },
)
