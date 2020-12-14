import argparse
from typing import Dict
from pathlib import Path

from kyoto_reader import KyotoReader


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', '-i', default=None, type=str,
                        help='path to input knp directory')
    parser.add_argument('--output-dir', '-o', default=None, type=str,
                        help='path to output knp directory')
    args = parser.parse_args()

    docs: Dict[str, str] = {}
    for path in Path(args.input_dir).glob('**/*.knp'):
        docs.update(KyotoReader.read_knp(path, did_from_sid=True))

    for did, knp_string in docs.items():
        out_path = Path(args.output_dir) / f'{did}.knp'
        with out_path.open(mode='w') as f:
            f.write(knp_string)


if __name__ == '__main__':
    main()
