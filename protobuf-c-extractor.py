import os.path
import sys
import argparse
from mmap import mmap
from enum import Enum

SIZE_OF_PROTOBUF_C_MESSAGE_DESCRIPTOR = 120
SIZE_OF_PROTOBUF_C_MESSAGE_FIELD_DESCRIPTOR = 72
SIZE_OF_PROTOBUF_C_MESSAGE_ENUM_DESCRIPTOR = 24
PROTOBUF_C_MESSAGE_DESCRIPTOR_MAGIC = b'\xf9\xee\xaa\x28\x00\x00\x00\x00'


class FieldLabel(Enum):
    PROTOBUF_C_LABEL_REQUIRED = 0
    PROTOBUF_C_LABEL_OPTIONAL = 1
    PROTOBUF_C_LABEL_REPEATED = 2
    PROTOBUF_C_LABEL_NONE = 3


class FieldType(Enum):
    PROTOBUF_C_TYPE_INT32 = 0
    PROTOBUF_C_TYPE_SINT32 = 1
    PROTOBUF_C_TYPE_SFIXED32 = 2
    PROTOBUF_C_TYPE_INT64 = 3
    PROTOBUF_C_TYPE_SINT64 = 4
    PROTOBUF_C_TYPE_SFIXED64 = 5
    PROTOBUF_C_TYPE_UINT32 = 6
    PROTOBUF_C_TYPE_FIXED32 = 7
    PROTOBUF_C_TYPE_UINT64 = 8
    PROTOBUF_C_TYPE_FIXED64 = 9
    PROTOBUF_C_TYPE_FLOAT = 10
    PROTOBUF_C_TYPE_DOUBLE = 11
    PROTOBUF_C_TYPE_BOOL = 12
    PROTOBUF_C_TYPE_ENUM = 13
    PROTOBUF_C_TYPE_STRING = 14
    PROTOBUF_C_TYPE_BYTES = 15
    PROTOBUF_C_TYPE_MESSAGE = 16


def get_string(mm, start):
    final_string = ""
    i = 0
    while mm[start + i]:
        final_string += chr(mm[start + i])
        i += 1

    return final_string


def process_label(label):
    return label.split("_")[-1].lower()


def process_protobuf_c_enum_descriptor_protofile(mm, location, iter_no=0, file=None):
    protofile = file
    if protofile:
        protofile.write("\n")
        print(f"\t" * iter_no + f"\t{location:#0x}> MAGIC: 0x114315af")

        name_ptr = int.from_bytes(mm[location + 8:location + 12], "little")
        name = get_string(mm, name_ptr)
        print(f"\t" * iter_no + f"\t{location + 8:#0x}> {name_ptr:#0x}> NAME:\t{name}")

        short_name_ptr = int.from_bytes(mm[location + 16:location + 20], "little")
        short_name = get_string(mm, short_name_ptr)
        print(f"\t" * iter_no + f"\t{location + 16:#0x}> {short_name_ptr:#0x}> SHORT NAME:\t{short_name}")

        c_name_ptr = int.from_bytes(mm[location + 24:location + 28], "little")
        c_name = get_string(mm, c_name_ptr)
        print(f"\t" * iter_no + f"\t{location + 24:#0x}> {c_name_ptr:#0x}> C NAME:\t{c_name}")

        package_name_ptr = int.from_bytes(mm[location + 32:location + 36], "little")
        package_name = get_string(mm, package_name_ptr)
        print(f"\t" * iter_no + f"\t{location + 32:#0x}> {package_name_ptr:#0x}> PACKAGE NAME:\t{package_name}")

        protofile.write(f"\t" * iter_no + f"enum {short_name} " + "{")
        protofile.write("\n")

        n_values = int.from_bytes(mm[location + 40:location + 44], 'little')
        print(f"\t" * iter_no + f"\t{location + 40:#0x}> N VALUES:\t{n_values}")

        values_prt = int.from_bytes(mm[location + 48:location + 52], 'little')
        for value in range(n_values):
            enum_name_ptr = int.from_bytes(mm[values_prt:values_prt + 4], "little")
            enum_name = get_string(mm, enum_name_ptr)
            print(f"\t" * iter_no + f"\t\t{values_prt:#0x}> {enum_name_ptr:#0x}> NAME:\t{enum_name}")

            enum_c_name_ptr = int.from_bytes(mm[values_prt + 8:values_prt + 12], "little")
            enum_c_name = get_string(mm, enum_c_name_ptr)
            print(f"\t" * iter_no + f"\t\t{values_prt + 8:#0x}> {enum_name_ptr:#0x}> C NAME:\t{enum_c_name}")

            enum_value = int.from_bytes(mm[values_prt + 16:values_prt + 20], 'little')
            print(f"\t" * iter_no + f"\t\t{values_prt + 16:#0x}> VALUE:\t{enum_value}")

            protofile.write(f"\t" * iter_no + f"\t{enum_name} = {enum_value};")
            protofile.write("\n")

            print()
            values_prt += SIZE_OF_PROTOBUF_C_MESSAGE_ENUM_DESCRIPTOR

        protofile.write(f"\t" * iter_no + "}")
        protofile.write("\n")
        protofile.write("\n")

        return short_name


def process_protobuf_c_message_descriptor_protofile(mm, location, out_dir=None, file=None, iter_no=0):
    print(f"\t" * iter_no + f"{location:#0x}> MAGIC: 0x28eeaaf9")

    name_ptr = int.from_bytes(mm[location + 8:location + 12], "little")
    name = get_string(mm, name_ptr)
    print(f"\t" * iter_no + f"{location + 8:#0x}> {name_ptr:#0x}> NAME:\t{name}")

    short_name_ptr = int.from_bytes(mm[location + 16:location + 20], "little")
    short_name = get_string(mm, short_name_ptr)
    print(f"\t" * iter_no + f"{location + 16:#0x}> {short_name_ptr:#0x}> SHORT NAME:\t{short_name}")

    c_name_ptr = int.from_bytes(mm[location + 24:location + 28], "little")
    c_name = get_string(mm, c_name_ptr)
    print(f"\t" * iter_no + f"{location + 24:#0x}> {c_name_ptr:#0x}> C NAME:\t{c_name}")

    package_name_ptr = int.from_bytes(mm[location + 32:location + 36], "little")
    package_name = get_string(mm, package_name_ptr)
    print(f"\t" * iter_no + f"{location + 32:#0x}> {package_name_ptr:#0x}> PACKAGE NAME:\t{package_name}")

    if file:
        protofile = file
    else:
        protofile = open(f"{os.path.join(out_dir, short_name)}.proto", "w")
        protofile.write("syntax = \"proto2\";")
        protofile.write("\n\n")
        if package_name:
            protofile.write(f"package {package_name};")
            protofile.write("\n\n")

    protofile.write(f"\t" * iter_no + "message " + short_name + " {")
    protofile.write("\n")

    print(f"\t" * iter_no + f"{location + 40:#0x}> SIZE:\t{int.from_bytes(mm[location + 40:location + 48], 'little')}")

    n_fields = int.from_bytes(mm[location + 48:location + 52], 'little')
    print(f"\t" * iter_no + f"{location + 48:#0x}> N FIELDS:\t{n_fields}")

    fields_ptr = int.from_bytes(mm[location + 56:location + 60], "little")
    print(f"\t" * iter_no + f"{location + 56:#0x}> {fields_ptr:#0x}> FIELDS")
    for field_no in range(1, n_fields + 1):
        field_name_ptr = int.from_bytes(mm[fields_ptr:fields_ptr + 4], "little")
        field_name = get_string(mm, field_name_ptr)
        print(f"\t" * iter_no + f"\t{fields_ptr:#0x}> {field_name_ptr:#0x}> NAME:\t{field_name}")

        identifier = int.from_bytes(mm[fields_ptr + 8: fields_ptr + 12], 'little')
        print(f"\t" * iter_no + f"\t{fields_ptr + 8:#0x}> ID:\t{identifier}")
        label = FieldLabel(int.from_bytes(mm[fields_ptr + 12: fields_ptr + 16], 'little'))
        print(f"\t" * iter_no + f"\t{fields_ptr + 12:#0x}> LABEL:\t{label.name}")
        type = FieldType(int.from_bytes(mm[fields_ptr + 16: fields_ptr + 20], 'little'))
        type_name = process_label(type.name)
        print(f"\t" * iter_no + f"\t{fields_ptr + 16:#0x}> TYPE:\t{type.name}")
        print(
            f"\t" * iter_no + f"\t{fields_ptr + 20:#0x}> QUANTIFIER OFFSET:\t{int.from_bytes(mm[fields_ptr + 20: fields_ptr + 24], 'little')}")
        print(
            f"\t" * iter_no + f"\t{fields_ptr + 24:#0x}> OFFSET:\t{int.from_bytes(mm[fields_ptr + 24: fields_ptr + 32], 'little')}")
        print(
            f"\t" * iter_no + f"\t{fields_ptr + 32:#0x}> DESCRIPTOR:\t{int.from_bytes(mm[fields_ptr + 32:fields_ptr + 36], 'little'):#0x}")

        if type == FieldType.PROTOBUF_C_TYPE_MESSAGE:
            protofile.write("\n")
            print()
            type_name = process_protobuf_c_message_descriptor_protofile(mm, int.from_bytes(
                mm[fields_ptr + 32:fields_ptr + 36], 'little'), iter_no=iter_no + 1, file=protofile)
        if type == FieldType.PROTOBUF_C_TYPE_ENUM:
            type_name = process_protobuf_c_enum_descriptor_protofile(mm,
                                                                     int.from_bytes(mm[fields_ptr + 32:fields_ptr + 36],
                                                                                    'little'), iter_no=iter_no + 1,
                                                                     file=protofile)

        protofile.write(f"\t" * iter_no + f"\t{process_label(label.name)} {type_name} {field_name} = {identifier};")
        protofile.write("\n")

        print(
            f"\t" * iter_no + f"\t{fields_ptr + 36:#0x}> DEFAULT VALUE:\t{int.from_bytes(mm[fields_ptr + 36:fields_ptr + 40], 'little')}")

        print("\t" * iter_no + "\t---")
        fields_ptr += SIZE_OF_PROTOBUF_C_MESSAGE_FIELD_DESCRIPTOR

    fields_sorted_ptr = int.from_bytes(mm[location + 64:location + 68], "little")
    print(f"\t" * iter_no + f"{location + 64:#0x}> {fields_sorted_ptr:#0x}> FIELDS SORTED")

    print(
        f"\t" * iter_no + f"{location + 72:#0x}> FIELD RANGES:\t{int.from_bytes(mm[location + 72:location + 76], 'little')}")

    message_init_ptr = int.from_bytes(mm[location + 80:location + 88], "little")
    print(f"\t" * iter_no + f"{location + 80:#0x}> {message_init_ptr:#0x}> MESSAGE INIT FUNC", )

    protofile.write(f"\t" * iter_no + "}")
    protofile.write("\n")
    protofile.write("\n")

    return short_name


def positions(mm):
    pos = -1
    while -1 != (pos := mm.find(PROTOBUF_C_MESSAGE_DESCRIPTOR_MAGIC, pos + 1)):
        yield pos


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", help="Binary from which extract .proto files")
    parser.add_argument("-o", "--output", help="Folder where put .proto files")
    args = parser.parse_args()

    if not args.input or not args.output:
        print("Usage: python3 protobuf-c-extractor.py -i/--input <binary_file> -o/--output <path_to_dir>")
        exit()

    if not os.path.exists(args.output):
        os.makedirs(args.output)

    print(f"FILE: {args.input}")
    with open(f"{args.input}", "r+b") as lfile:
        with mmap(lfile.fileno(), 0) as mapping:

            file_magic = mapping[:4]
            if file_magic == b'\xca\xfe\xba\xbe':
                print("!!! This script does not work with FAT binaries !!!")
                print("Please extract the binary for one arch before.")
                exit()

            for pos in positions(mapping):
                process_protobuf_c_message_descriptor_protofile(mapping, pos, out_dir=args.output)
                print()
                print("#" * 50)
                print()
