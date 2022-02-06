from pyais.messages import MSG_CLASS

for typ, cls in MSG_CLASS.items():
    if not cls.fields():
        continue
    print(cls.__name__, cls.__doc__)
    print()
    print("\tAttributes:")
    for field in cls.fields():
        print("\t\t*", f"`{field.name}`")
        if 'mmsi' in field.name:
            print("\t\t\t*", "type:", f"({int}, {str})")
        else:
            print("\t\t\t*", "type:", field.metadata['d_type'])
        print("\t\t\t*", "bit-width:", field.metadata['width'])
        print("\t\t\t*", "default:", field.metadata['default'])
