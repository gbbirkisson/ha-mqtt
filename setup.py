import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ha_mqtt",
    version="0.0.1",
    author="Guðmundur Björn Birkisson",
    author_email="gbbirkisson@gmail.com",
    description="A small package that helps with mqtt communication with Home Assistant",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gbbirkisson/ha-mqtt",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU LGPLv3 License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        'paho-mqtt>=1.4.0',
        'PyYAML'
    ]
)
