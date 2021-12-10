SUPPORTED_DEVICE_TYPES = {
    b'\x92\x01\x42\x00': 'eds_files/MCLM3002P-CO.eds',
    b'\x92\x01\x02\x00': 'eds_files/maxon_EPOS4_50-5.eds',
}


from pprint import pprint, pformat
import json


print('SUPPORTED_DEVICE_TYPES')
print(SUPPORTED_DEVICE_TYPES)
print()

print('repr(SUPPORTED_DEVICE_TYPES)')
print(repr(SUPPORTED_DEVICE_TYPES))
print()

print('pprint(SUPPORTED_DEVICE_TYPES)')
s = pformat(SUPPORTED_DEVICE_TYPES)
print(s)
print()

print(json.dumps(SUPPORTED_DEVICE_TYPES, indent=2))
