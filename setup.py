"""
Установочный скрипт для Solana Token Deployer
"""

from setuptools import setup, find_packages
import os

# Читаем README файл
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Читаем requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="solana-token-deployer",
    version="1.0.0",
    author="Solana Token Deployer Team",
    author_email="contact@solana-token-deployer.com",
    description="Автоматизированная система для создания, развертывания и управления SPL токенами в сети Solana",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/solana-token-deployer/solana-token-deployer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.991",
            "pre-commit>=2.20.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
            "myst-parser>=0.18.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "solana-token-deployer=main:app",
            "std=main:app",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.txt", "*.md"],
    },
    zip_safe=False,
)
