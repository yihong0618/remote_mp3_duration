from setuptools import setup

setup(
    name="remote_mp3_duration",
    author="yihong0618",
    author_email="zouzou0208@gmail.com",
    url="https://github.com/yihong0618/remote_mp3_duration",
    license="MIT",
    version="0.1.0",
    install_requires=["requests"],
    entry_points={
        "console_scripts": ["mp3_duration = mp3_duration.cli:main"],
    },
)
