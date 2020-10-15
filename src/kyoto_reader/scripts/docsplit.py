import re
import argparse
from typing import Dict
from pathlib import Path

SID_PTN = re.compile(r'^# S-ID:\s*([a-zA-Z0-9-_]+)-(\d+) .*$')


def read(path: Path) -> Dict[str, str]:
    docs: Dict[str, str] = {}
    did = None
    with path.open() as f:
        buff = ''
        for line in f:
            if line.startswith('# S-ID'):
                match = SID_PTN.match(line.strip())
                # sid = match.group(1) + '-' + match.group(2)
                if did != match.group(1):
                    if did is not None:
                        docs[did] = buff
                        buff = ''
                    did = match.group(1)
            buff += line
        docs[did] = buff
    return docs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', '-i', default=None, type=str,
                        help='path to input knp directory')
    parser.add_argument('--output-dir', '-o', default=None, type=str,
                        help='path to output knp directory')
    args = parser.parse_args()

    docs: Dict[str, str] = {}
    for path in Path(args.input_dir).glob('**/*.knp'):
        docs.update(read(path))

    for did, knp_string in docs.items():
        out_path = Path(args.output_dir) / f'{did}.knp'
        with out_path.open(mode='w') as f:
            f.write(knp_string)


if __name__ == '__main__':
    main()
