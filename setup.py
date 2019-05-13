from setuptools import setup, find_packages
import io
import os

here = os.path.abspath(os.path.dirname(__file__))

# Avoids IDE errors, but actual version is read from version.py
__version__ = None
exec (open("rasa_sdk/version.py").read())

# Get the long description from the README file
with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

tests_requires = ["pytest~=3.0", "pytest-pep8~=1.0", "pytest-cov~=2.0"]


install_requires = [
    "future~=0.17",
    "ConfigArgParse~=0.14",
    "coloredlogs~=10.0",
    "flask~=1.0",
    "flask_cors~=3.0",
    "gevent>=1.4",
    "six>=1.10",
]

extras_requires = {"test": tests_requires, ":python_version < '3.5'": ["typing~=3.0"]}

setup(
    name="rasa-sdk",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        # supported python versions
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Libraries",
    ],
    packages=find_packages(exclude=["tests", "tools"]),
    version=__version__,
    install_requires=install_requires,
    tests_require=tests_requires,
    extras_require=extras_requires,
    include_package_data=True,
    description="Machine learning based dialogue engine "
    "for conversational software.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Rasa Technologies GmbH",
    author_email="hi@rasa.com",
    maintainer="Tom Bocklisch",
    maintainer_email="tom@rasa.com",
    license="Apache 2.0",
    keywords="nlp machine-learning machine-learning-library bot bots "
    "botkit rasa conversational-agents conversational-ai chatbot"
    "chatbot-framework bot-framework",
    url="https://rasa.com",
    download_url="https://github.com/RasaHQ/rasa-sdk/archive/{}.tar.gz"
    "".format(__version__),
    project_urls={
        "Bug Reports": "https://github.com/rasahq/rasa-sdk/issues",
        "Documentation": "https://rasa.com/docs",
        "Source": "https://github.com/rasahq/rasa-sdk",
    },
)

print ("\nWelcome to Rasa SDK!")
print ("If any questions please visit documentation page https://rasa.com/docs")
print ("or join the community discussions on https://forum.rasa.com")
