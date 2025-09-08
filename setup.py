from setuptools import setup, find_packages

setup(
    name="pydantic_utcp_adapters",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'pydantic>=2.0.0',
        'aiohttp>=3.8.0',
        'pyyaml>=6.0',
        'utcp',
        'utcp-http',
    ],
    python_requires='>=3.8',
)
