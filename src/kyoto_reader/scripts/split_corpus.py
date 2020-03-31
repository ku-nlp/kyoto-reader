import re
import sys
import argparse
from typing import Dict
from pathlib import Path


# cat 9798673.knp | python split_corpus.py --output-dir knp

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', '-o', default=None, type=str,
                        help='path to output knp directory')
    args = parser.parse_args()

    sid_pat = re.compile(r'^# S-ID:(\d{9})-(\d{3}) .*$')

    docs: Dict[str, str] = {}
    did = None
    buff = ''
    for line in sys.stdin:
        if line.startswith('# S-ID'):
            match = sid_pat.match(line.strip())
            # sid = match.group(1) + '-' + match.group(2)
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
