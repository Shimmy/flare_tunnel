from setuptools import setup, find_packages
import os

# Read the content of README.md
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="flare-tunnel",
    version="0.1.0",
    description="A simple Cloudflare tunnel wrapper similar to ngrok",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Flare Team",
    author_email="noreply@example.com",
    url="https://github.com/yourusername/flare-tunnel",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    entry_points={
        "console_scripts": [
            "flare=flare.cli:run",
        ],
    },
    python_requires=">=3.6",
    keywords="cloudflare, tunnel, ngrok, development, networking",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/flare-tunnel/issues",
        "Documentation": "https://github.com/yourusername/flare-tunnel#readme",
        "Source Code": "https://github.com/yourusername/flare-tunnel",
    },
)