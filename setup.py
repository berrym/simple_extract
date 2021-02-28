import setuptools

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name="simple_extract",
    version="0.1.5",
    packages=[""],
    python_requires=">=3.6",
    url="https://github.com/berrym/simple_extract.git",
    author="Michael Berry",
    author_email="trismegustis@gmail.com",
    description="A small command line utility to help extract compressed archives.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    entry_points={
        "console_scripts": [
            "simple-extract = simple_extract:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
