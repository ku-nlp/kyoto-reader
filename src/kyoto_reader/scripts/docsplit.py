import re
import argparse
from typing import Dict
from pathlib import Path


# python split_corpus.py --input-dir /somewhere/kc/input --output-dir /somewhere/kc/output

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', '-i', default=None, type=str,
                        help='path to input knp directory')
    parser.add_argument('--output-dir', '-o', default=None, type=str,
                        help='path to output knp directory')
    args = parser.parse_args()

    sid_pat = re.compile(r'^# S-ID:((\d{9})|(w\d{6}-\d{10}))-([0-9-]+) .*$')

    docs: Dict[str, str] = {}
    did = None
    for path in Path(args.input_dir).glob('**/*.knp'):
        with path.open() as f:
            buff = ''
            for line in f:
                if line.startswith('# S-ID'):
                    match = sid_pat.match(line.strip())
                    # sid = match.group(1) + '-' + match.group(4)
                    if did != match.group(1):
                        if did is not None:
                            docs[did] = buff
                            buff = ''
                        did = match.group(1)
                buff += line
            docs[did] = buff

    output_dir = Path(args.output_dir)
    for did, knp_string in docs.items():
        with output_dir.joinpath(f'{did}.knp').open(mode='w') as f:
            f.write(knp_string)


if __name__ == '__main__':
    main()
