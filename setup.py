import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="nicehash2mqtt",
    version="0.0.16",
    author="Nicolas Slythe",
    author_email="nicehash2mqtt@slythe.net",
    description="Bridge between nicehash and mqtt",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nslythe/nicehash2mqtt",
    project_urls={
        "Bug Tracker": "https://github.com/nslythe/nicehash2mqtt/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={'console_scripts':['nicehash2mqtt = nicehash2mqtt:main'] },
    py_modules=["nicehash2mqtt"],
    package_dir={"": "."},
    packages=setuptools.find_packages(where="."),
    python_requires=">=3.6",
    install_requires=["pynicehash", "paho-mqtt"]
)