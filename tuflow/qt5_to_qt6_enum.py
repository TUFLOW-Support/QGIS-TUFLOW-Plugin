from pathlib import Path
from collections import OrderedDict


def enums():
    enums = OrderedDict()
    comp_file = Path(__file__).parent / 'compatibility_routines.py'
    start = False
    with comp_file.open() as f:
        for line in f:
            if '# PyQt5/PyQt6 enumerators' in line:
                start = True
                while 'else' not in line and line != '':
                    line = f.readline()
                continue
            elif '# end PyQt5/PyQt6 enumerators' in line:
                break
            if not start:
                continue
            if not line.strip() or line.strip().startswith('#'):
                continue
            val, key = line.strip().split(' = ', 1)
            key1 = f'QtCore.{key}'
            enums[key1] = val
            key1 = f'QtGui.{key}'
            enums[key1] = val
            key1 = f'QtWidgets.{key}'
            enums[key1] = val
            key1 = f'QtMultimedia.{key}'
            enums[key1] = val
            key1 = f'QtNetwork.{key}'
            enums[key1] = val
            key1 = f'QtQml.{key}'
            enums[key1] = val
            enums[key] = val
    return enums


def main():
    e = enums()
    p = Path(__file__).parent
    for file in p.glob('**/*.py'):
        if file.name in ['compatibility_routines.py', 'qt5_to_qt6_enum.py']:
            continue
        with file.open('r') as f:
            lines = f.readlines()
        new_lines = []
        import_req = []
        import_str = 'from ' + '.' * (len(file.parents) - len(p.parents)) + 'compatibility_routines import '
        import_line_idx = -1
        import_already_exists = False
        for i, line in enumerate(lines):
            if 'compatibility_routines import ' in line and import_line_idx == -1:
                import_already_exists = True
                import_line_idx = i
                import_req = [x.strip() for x in line.split('import ')[1].split(',')]
                import_str = line.split('import')[0] + 'import '
                continue
            if line.startswith('class') or line.startswith('def'):
                if import_line_idx == -1:
                    import_line_idx = i
            for key, val in e.items():
                if key in line:
                    line = line.replace(key, val)
                    if val not in import_req:
                        import_req.append(val)
            new_lines.append(line)

        if import_req:
            import_req = [i.strip() for i in import_req]
            import_req = list(set(import_req))
            import_str += ', '.join(import_req)
            if not import_already_exists:
                import_str = f'\n{import_str}\n\n'
            new_lines.insert(import_line_idx, f'{import_str}\n')

        with file.open('w') as f:
            for line in new_lines:
                f.write(line)


if __name__ == '__main__':
    main()
