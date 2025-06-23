"""
Copyright (c) Cutleast
"""

import logging
import zlib
from io import BufferedReader, BytesIO

from .datatypes import Hex, Integer
from .flags import RecordFlags
from .subrecord import SUBRECORD_MAP, StringSubrecord, Subrecord
from .utilities import STRING_RECORDS, get_checksum, peek, prettyprint_object


class Record:
    """
    Contains parsed record data.
    """

    type: str
    size: int
    flags: RecordFlags
    formid: str
    timestamp: int
    version_control_info: int
    internal_version: int
    unknown: int
    data: bytes

    subrecords: list[Subrecord]

    log = logging.getLogger("PluginParser")

    def __repr__(self) -> str:
        return prettyprint_object(self)

    def __len__(self):
        return len(self.dump())

    def parse(self, stream: BufferedReader, header_flags: RecordFlags):
        self.type = stream.read(4).decode()
        self.size = Integer.parse(stream, Integer.IntType.UInt32)
        self.flags = RecordFlags.parse(stream, Integer.IntType.UInt32)
        self.formid = Hex.parse(stream)
        self.timestamp = Integer.parse(stream, Integer.IntType.UInt16)
        self.version_control_info = Integer.parse(stream, Integer.IntType.UInt16)
        self.internal_version = Integer.parse(stream, Integer.IntType.UInt16)
        self.unknown = Integer.parse(stream, Integer.IntType.UInt16)

        # Decompress data if compressed
        if RecordFlags.Compressed in self.flags:
            decompressed_size = Integer.parse(stream, Integer.IntType.UInt32)
            self.data = zlib.decompress(stream.read(self.size - 4))
            self.size = decompressed_size
        else:
            self.data = stream.read(self.size)

        # Parse subrecords (also known as fields)
        match self.type:
            case "INFO":
                self.parse_info_record(header_flags)
            case "PERK":
                self.parse_perk_record(header_flags)
            case "QUST":
                self.parse_qust_record(header_flags)
            case _:
                self.parse_subrecords(header_flags)

    def parse_qust_record(self, header_flags: RecordFlags):
        stream = BytesIO(self.data)
        self.subrecords = []

        def calc_condition_index(stage_index: int) -> int:
            """
            Creates unique index from hashes of previous array
            of CTDA subrecords.
            """

            ctda_subrecords: list[Subrecord] = []

            for subrecord in self.subrecords[::-1]:
                if subrecord.type == "CTDA":
                    ctda_subrecords.append(subrecord)
                else:
                    break

            hashes: list[int] = []

            for subrecord in ctda_subrecords[::-1]:
                value = abs(hash(subrecord.data))
                hashes.append(value)

            index = get_checksum(sum(hashes) - stage_index)

            return index

        current_stage_index = 0
        current_objective_index = 0

        while stream.tell() < len(self.data):
            subrecord_type = peek(stream, 4).decode()

            if subrecord_type in STRING_RECORDS.get(self.type, []):
                subrecord = StringSubrecord(subrecord_type)
            else:
                subrecord: Subrecord = SUBRECORD_MAP.get(subrecord_type, Subrecord)()

            subrecord.parse(stream, header_flags)

            match subrecord_type:
                # Calculate stage "index" from INDX subrecord
                case "INDX":
                    current_stage_index = abs(hash(subrecord.data))

                # Set current log entry index as index of string
                case "CNAM":
                    subrecord.index = calc_condition_index(current_stage_index)

                # Get quest objective index
                case "QOBJ":
                    current_objective_index = subrecord.index

                # Set current objective index as index of string
                case "NNAM":
                    subrecord.index = current_objective_index

            self.subrecords.append(subrecord)

    def parse_info_record(self, header_flags: RecordFlags):
        stream = BytesIO(self.data)
        self.subrecords = []
        current_index = 0

        while stream.tell() < len(self.data):
            subrecord_type = peek(stream, 4).decode()

            if subrecord_type in STRING_RECORDS.get(self.type, []):
                subrecord = StringSubrecord(subrecord_type)
            else:
                subrecord: Subrecord = SUBRECORD_MAP.get(subrecord_type, Subrecord)()

            subrecord.parse(stream, header_flags)

            match subrecord_type:
                # Get response id
                case "TRDT":
                    current_index = subrecord.response_id

                # Set current response id as index of string
                case "NAM1":
                    subrecord.index = current_index

            self.subrecords.append(subrecord)

    def parse_perk_record(self, header_flags: RecordFlags):
        stream = BytesIO(self.data)
        self.subrecords = []

        perk_type = None
        epfd_index = 0

        while stream.tell() < len(self.data):
            subrecord_type = peek(stream, 4).decode()

            if (perk_type == 4 and subrecord_type == "EPF2") or (
                perk_type == 7 and subrecord_type == "EPFD"
            ):
                subrecord = StringSubrecord(subrecord_type)
            else:
                subrecord: Subrecord = SUBRECORD_MAP.get(subrecord_type, Subrecord)()

            subrecord.parse(stream, header_flags)
            self.subrecords.append(subrecord)

            match subrecord_type:
                case "EPFT":
                    perk_type = subrecord.perk_type

                case "EPFD":
                    subrecord.index = epfd_index
                    epfd_index += 1

                case "EPF2":
                    if peek(stream, 4) == b"EPF3":
                        index_subrecord = Subrecord()
                        index_subrecord.parse(stream, header_flags)
                        epf2_index = int.from_bytes(
                            index_subrecord.data[2:], byteorder="little"
                        )
                        subrecord.index = epf2_index
                        self.subrecords.append(index_subrecord)

                    else:
                        self.log.warning(
                            f"EPF2 Subrecord without following EPF3! Record: {self}"
                        )

    def parse_subrecords(self, header_flags: RecordFlags):
        stream = BytesIO(self.data)
        self.subrecords = []
        itxt_index = 0

        while stream.tell() < len(self.data):
            subrecord_type = peek(stream, 4).decode()

            if subrecord_type in STRING_RECORDS.get(self.type, []):
                subrecord = StringSubrecord(subrecord_type)
            else:
                subrecord: Subrecord = SUBRECORD_MAP.get(subrecord_type, Subrecord)()

            subrecord.parse(stream, header_flags)

            if subrecord.type == "ITXT":
                subrecord.index = itxt_index
                itxt_index += 1

            self.subrecords.append(subrecord)

    def dump(self) -> bytes:
        # Prepare Data field
        data = b"".join(subrecord.dump() for subrecord in self.subrecords)

        if RecordFlags.Compressed in self.flags:
            uncompressed_size = Integer.dump(len(data), Integer.IntType.UInt32)
            data = uncompressed_size + zlib.compress(data)

        self.size = len(data)

        # Combine all values
        self.data = b""
        self.data += self.type.encode()
        self.data += Integer.dump(self.size, Integer.IntType.UInt32)
        self.data += RecordFlags.dump(self.flags, Integer.IntType.UInt32)
        self.data += Hex.dump(self.formid)
        self.data += Integer.dump(self.timestamp, Integer.IntType.UInt16)
        self.data += Integer.dump(self.version_control_info, Integer.IntType.UInt16)
        self.data += Integer.dump(self.internal_version, Integer.IntType.UInt16)
        self.data += Integer.dump(self.unknown, Integer.IntType.UInt16)
        self.data += data

        return self.data
