import re

import requests


class ID3V2Header:
    def __init__(self, size: int, header_size: int):
        self.size = size
        self.header_size = header_size


class MP3FrameHeader:
    def __init__(
        self,
        bitrate: int,
        sampling_rate: int,
        stereo: bool,
        mpeg_version_bits: int,
        layer_bits: int,
        bitrate_bits: int,
        sampling_rate_bits: int,
        channel_mode_bits: int,
    ):
        self.bitrate = bitrate
        self.sampling_rate = sampling_rate
        self.stereo = stereo
        self.mpeg_version_bits = mpeg_version_bits
        self.layer_bits = layer_bits
        self.bitrate_bits = bitrate_bits
        self.sampling_rate_bits = sampling_rate_bits
        self.channel_mode_bits = channel_mode_bits


bitrates = [
    [
        # MPEG 2.5
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # LayerReserved
        [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],  # Layer3
        [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],  # Layer2
        [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],  # Layer1
    ],
    [
        # Reserved
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # LayerReserved
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # Layer3
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # Layer2
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # Layer1
    ],
    [
        # MPEG 2
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # LayerReserved
        [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],  # Layer3
        [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],  # Layer2
        [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],  # Layer1
    ],
    [
        # MPEG 1
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # LayerReserved
        [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],  # Layer3
        [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384],  # Layer2
        [
            0,
            32,
            64,
            96,
            128,
            160,
            192,
            224,
            256,
            288,
            320,
            352,
            384,
            416,
            448,
        ],  # Layer1
    ],
]

sampling_rates = [
    # MPEG 2.5
    [11025, 12000, 8000, 0],
    # Reserved
    [0, 0, 0, 0],
    # MPEG 2
    [22050, 24000, 16000, 0],
    # MPEG 1
    [44100, 48000, 32000, 0],
]


class BytesRangeData:
    def __init__(self, data, data_range):
        self.data = data
        self.data_range = data_range


class FetchDataReader:
    range_regex = re.compile(r"([^\s]+)\s((([\d]+)-([\d]+))|\*)/([\d]+|\*)")

    def __init__(self, url):
        self.url = url

    def get_total_length(self):
        response = requests.head(self.url)
        content_length = response.headers.get("content-length")
        if content_length is not None:
            total_content_size = int(content_length)
            return total_content_size
        return None

    def read_bytes_range(self, start, end=None):
        headers = {
            "Range": f"bytes={start}-{end}" if end is not None else f"bytes={start}-"
        }
        response = requests.get(self.url, headers=headers)
        array_buffer = response.content
        range_string = response.headers.get("content-range")
        data_range = None

        if range_string:
            match = self.range_regex.match(range_string)
            if match:
                unit, start, end, size = (
                    match.groups()[0],
                    int(match.groups()[3]),
                    int(match.groups()[4]),
                    int(match.groups()[5]),
                )
                data_range = {"unit": unit, "start": start, "end": end, "size": size}

        return BytesRangeData(list(array_buffer), data_range)


def read_synchsafe_integer(buffer, size, offset=0):
    mask = 0x7F
    out = 0

    for i in range(size):
        out = (out << 7) | (buffer[i + offset] & mask)
    return out


def read_id3v2_header(bytes_range_data):
    data = bytes_range_data.data
    total_content_size = None
    if bytes_range_data.data_range:
        total_content_size = bytes_range_data.data_range.get("size")
    if data[0] == 0x49 and data[1] == 0x44 and data[2] == 0x33:
        return {
            "header": {"header_size": 10, "size": read_synchsafe_integer(data, 4, 6)},
            "data": data,
            "total_content_size": total_content_size,
        }
    else:
        return {"total_content_size": total_content_size, "data": data}


def parse_mp3_frame_header(header, offset):
    first_ui16be = header[1] | (header[0] << 8)
    sync_word = first_ui16be & 0xFFE0
    if sync_word != 0xFFE0:
        raise ValueError(f"Malformed MP3 file - frame not found at {offset}")

    mpeg_version_bits = (first_ui16be >> 3) & 0x3
    layer_bits = (first_ui16be >> 1) & 0x3
    bitrate_bits = (header[2] & 0xF0) >> 4
    sampling_rate_bits = (header[2] & 0x0F) >> 4
    channel_mode_bits = header[3] >> 6

    return {
        "bitrate": bitrates[mpeg_version_bits][layer_bits][bitrate_bits],
        "stereo": channel_mode_bits != 3,
        "sampling_rate": sampling_rates[mpeg_version_bits][sampling_rate_bits],
        "bitrate_bits": bitrate_bits,
        "layer_bits": layer_bits,
        "mpeg_version_bits": mpeg_version_bits,
        "sampling_rate_bits": sampling_rate_bits,
        "channel_mode_bits": channel_mode_bits,
    }


def get_mp3_duration(url):
    f = FetchDataReader(url)
    data = read_id3v2_header(f.read_bytes_range(0, 9))
    header = data.get("header", {})
    mp3_data = data.get("data")
    total_content_size = data.get("total_content_size")
    if not total_content_size:
        total_content_size = f.get_total_length()
        if not total_content_size:
            return 0
    first_frame_offset = header.get("size", 0) + header.get("header_size", 0)
    total_audio_data_size = total_content_size - first_frame_offset
    if first_frame_offset == 0:
        mp3_frame_header = parse_mp3_frame_header(mp3_data, first_frame_offset)
    else:
        res = f.read_bytes_range(first_frame_offset, first_frame_offset + 3)
        mp3_frame_header = parse_mp3_frame_header(res.data, first_frame_offset)
    return int(
        (total_audio_data_size / ((mp3_frame_header["bitrate"] / 8) * 1000))
        * (1 if mp3_frame_header["stereo"] else 2)
    )


if __name__ == "__main__":
    print(
        get_mp3_duration(
            "https://chrt.fm/track/6AGABB/r.typlog.com/eyJzIjozNTIsImUiOjcxODY5LCJ0IjoxfQ.Ogqkth3_259fCin-j60aIYSXVUk/pythonhunter/8302654647_51408.mp3"
        )
    )
