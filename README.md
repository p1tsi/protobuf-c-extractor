# protobuf-c-extractor
If for some strange reason you need to get the .proto files embedded in mach-o binaries using libprotobuf-c library, let's have a try with this script.

NB: this script does not work with fat binaries. Extract the binary for one architecture before using it.

## Usage
```
python3 protobuf-c-extractor.py -i sample -o /tmp
```

# Example
Inside `samples` folder there are a few .proto files extracted from Telegram macOS application.
