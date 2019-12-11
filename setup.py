import io
import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

# Avoids IDE errors, but actual version is read from version.py
__version__ = None
exec(open("rasa_sdk/version.py").read())

# Get the long description from the README file
with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

tests_requires = ["pytest~=4.0", "pytest-cov~=2.0"]

install_requires = [
    "ConfigArgParse>=0.14",
    "coloredlogs~=10.0",
    "sanic~=19.9",
    "sanic-cors==0.9.9.post1",
    # needed because of https://github.com/huge-success/sanic/issues/1729
    "multidict==4.6.1",
]

extras_requires = {"test": tests_requires}

setup(
    name="rasa-sdk",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        # supported python versions
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Libraries",
    ],
    python_requires=">=3.6",
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
    download_url=f"https://github.com/RasaHQ/rasa-sdk/archive/{__version__}.tar.gz",
    project_urls={
        "Bug Reports": "https://github.com/rasahq/rasa-sdk/issues",
        "Documentation": "https://rasa.com/docs",
        "Source": "https://github.com/rasahq/rasa-sdk",
    },
)

print("\nWelcome to Rasa SDK!")
print("If any questions please visit documentation page https://rasa.com/docs")
print("or join the community discussions on https://forum.rasa.com")
