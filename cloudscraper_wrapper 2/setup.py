from setuptools import setup, find_packages

setup(
    name="cloudscraper_wrapper",
    version="0.1.3",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        'cloudscraper>=1.2.60',
        'requests>=2.25.0',
    ],
    python_requires='>=3.7',
    author="pedro-flow",
    author_email="pedroflowss@gmail.com",
    description="A modern wrapper for CloudScraper with caching and rate limiting",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/pedro-flow/cloudscraper-wrapper",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)