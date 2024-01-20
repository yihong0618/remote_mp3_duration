import argparse

from mp3_duration.mp3_duration import get_mp3_duration


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="remote mp3 url")
    options = parser.parse_args()
    print(get_mp3_duration(options.url))


if __name__ == "__main__":
    main()
