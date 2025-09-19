import os.path
import sys
import argparse
from mmap import mmap
from enum import Enum
import r2pipe


SIZE_OF_PROTOBUF_C_MESSAGE_DESCRIPTOR = 120
SIZE_OF_PROTOBUF_C_MESSAGE_FIELD_DESCRIPTOR = 72
SIZE_OF_PROTOBUF_C_MESSAGE_ENUM_DESCRIPTOR = 24
PROTOBUF_C_MESSAGE_DESCRIPTOR_MAGIC = b'\xf9\xee\xaa\x28\x00\x00\x00\x00'
PROTOBUF_C_MESSAGE_DESCRIPTOR_MAGIC_STR = "f9eeaa2800000000"

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


def process_label(label):
    return label.split("_")[-1].lower()


def get_string(string_offset):
    str_ptr = r2.cmd(f"pv4 @ {string_offset}")
    string = r2.cmd(f"ps @ {str_ptr}")

    return string.strip()


def get_pb_enum(enum_offset, iter_no=0, file=None):
    prefix = "\t"*(iter_no)

    magic = r2.cmd(f"px0 @ {enum_offset}").strip()
    print(f"{prefix}ENUM MAGIC: {magic}")

    file.write("\n")

    name = get_string(f"{enum_offset}+0x8")
    print(f"{prefix}NAME: {name}")

    short_name = get_string(f"{enum_offset}+0x10")
    print(f"{prefix}SHORT NAME: {short_name}")

    c_name = get_string(f"{enum_offset}+0x18")
    print(f"{prefix}C NAME: {c_name}")

    package_name = get_string(f"{enum_offset}+0x20")
    print(f"{prefix}PACKAGE NAME: {package_name}")

    file.write(f"{prefix}enum {short_name} " + "{")
    file.write("\n")

    values_count = int(r2.cmd(f"pv1px  @ {enum_offset}+0x28"), 16)
    print(f"{prefix}VALUES COUNT: {values_count}")

    values_ptr = r2.cmd(f'pv4 @ {enum_offset}+0x30').strip()

    for i in range(values_count):
        cur_value_ptr = f"{values_ptr} + {SIZE_OF_PROTOBUF_C_MESSAGE_ENUM_DESCRIPTOR*i}"

        value_name = get_string(cur_value_ptr)
        print(f"{prefix}\tVALUE NAME: {value_name}")

        c_name = get_string(f"{cur_value_ptr}+0x8")
        print(f"{prefix}\tC NAME: {c_name}")

        value = int(r2.cmd(f"pv4 @ {cur_value_ptr}+0x10"), 16)
        print(f"{prefix}\tVALUE: {value}")

        file.write(f"{prefix}\t{value_name} = {value};")
        file.write("\n")
    
    file.write(f"{prefix}" + "}")
    file.write("\n")
    file.write("\n")

    return short_name


def get_pb_struct(struct_offset, iter_no=0, out_dir=None, file=None):

    prefix = "\t"*iter_no

    name = get_string(f"{struct_offset}+0x8")
    print(f"{prefix}NAME: {name}")
    
    short_name = get_string(f"{struct_offset}+0x10")
    print(f"{prefix}SHORT NAME: {short_name}")

    c_name = get_string(f"{struct_offset}+0x18")
    print(f"{prefix}C NAME: {c_name}")
    
    package_name = get_string(f"{struct_offset}+0x20")
    print(f"{prefix}PACKAGE NAME: {package_name}")
    
    size = int(r2.cmd(f'pv8 @ {struct_offset}+0x28'), 16)
    print(f"{prefix}SIZE: {size}")

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


    field_count = int(r2.cmd(f"pv1 @ {struct_offset}+0x30"), 16)
    print(f"{prefix}FIELD COUNT: {field_count}")
    
    fields_ptr = r2.cmd(f'pv4 @ {struct_offset}+0x38').strip()

    for i in range(field_count):
        cur_field_ptr = f"{fields_ptr} + {SIZE_OF_PROTOBUF_C_MESSAGE_FIELD_DESCRIPTOR*i}"
        field_name = get_string(cur_field_ptr)
        print(f"{prefix}\tFIELD NAME: {field_name}")

        field_id = int(r2.cmd(f"pv4 @ {cur_field_ptr}+0x8"), 16)
        print(f"{prefix}\tFIELD ID: {field_id}")
        
        field_label = FieldLabel(int(r2.cmd(f"pv4 @ {cur_field_ptr}+0xc"), 16))
        print(f"{prefix}\tFIELD LABEL: {field_label.name}")
        
        field_type = FieldType(int(r2.cmd(f"pv4 @ {cur_field_ptr}+0x10"), 16))
        print(f"{prefix}\tFIELD TYPE: {field_type.name}")
        type_name = process_label(field_type.name)

        quantifier = int(r2.cmd(f"pv4 @ {cur_field_ptr}+0x14"), 16)
        print(f"{prefix}\tQUANTIFIER: {quantifier}")

        off = int(r2.cmd(f"pv8 @ {cur_field_ptr}+0x18"), 16)
        print(f"{prefix}\tOFFSET: {off}")

        descriptor = r2.cmd(f"pv4 @ {cur_field_ptr}+0x20").strip()
        print(f"{prefix}\tDESCRIPTOR: {descriptor}")

        if field_type == FieldType.PROTOBUF_C_TYPE_MESSAGE:
            protofile.write("\n")
            type_name = get_pb_struct(descriptor, iter_no=iter_no+1, file=protofile)
        
        if field_type == FieldType.PROTOBUF_C_TYPE_ENUM:
            type_name = get_pb_enum(descriptor, iter_no=iter_no+1, file=protofile)

        protofile.write(f"\t" * iter_no + f"\t{process_label(field_label.name)} {type_name} {field_name} = {field_id};")
        protofile.write("\n")
        
        default_value = int(r2.cmd(f"pv4 @ {cur_field_ptr}+0x24"), 16)
        print(f"{prefix}\tDEFAULT VALUE: {default_value}")
            
        print()
    

    protofile.write(f"\t" * iter_no + "}")
    protofile.write("\n")
    protofile.write("\n")

    return short_name


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
    file = args.input
    r2 = r2pipe.open(file)

    pb_struct_list = r2.cmdj(f"/xj {PROTOBUF_C_MESSAGE_DESCRIPTOR_MAGIC_STR}")
    for pb_struct in pb_struct_list:

        struct_offset = pb_struct['offset']
        get_pb_struct(struct_offset, out_dir=args.output)



