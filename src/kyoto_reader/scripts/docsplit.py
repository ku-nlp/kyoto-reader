import argparse
from pathlib import Path

from kyoto_reader import KyotoReader


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', '-i', default=None, type=str,
                        help='path to input knp directory')
    parser.add_argument('--output-dir', '-o', default=None, type=str,
                        help='path to output knp directory')
    args = parser.parse_args()

    reader = KyotoReader(args.input_dir, did_from_sid=True)

    for did in reader.doc_ids:
        out_path = Path(args.output_dir) / f'{did}.knp'
        with out_path.open(mode='w') as f:
            f.write(reader.get_knp(did))


if __name__ == '__main__':
    main()
