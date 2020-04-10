import sys
import argparse
from pathlib import Path
import shutil


def main():
    """id ファイルを参照してコーパスファイルを train と valid (dev) と test ディレクトリにコピーする"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--corpus-dir', '-c', required=True, type=str,
                        help='path to directory where all corpus files exist')
    parser.add_argument('--output-dir', '-o', required=True, type=str,
                        help='path to directory where copied files will be saved')
    parser.add_argument('--train', default=None, type=str,
                        help='path to train id file')
    parser.add_argument('--dev', default=None, type=str,
                        help='path to dev id file')
    parser.add_argument('--valid', default=None, type=str,
                        help='path to valid id file')
    parser.add_argument('--test', default=None, type=str,
                        help='path to test id file')
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir)
    output_dir = Path(args.output_dir)

    if args.dev and args.valid:
        print('Specify either --dev or --valid', file=sys.stderr)
        exit(1)

    if args.train:
        write(Path(args.train), output_dir / 'train', corpus_dir)
    if args.dev:
        write(Path(args.dev), output_dir / 'dev', corpus_dir)
    if args.valid:
        write(Path(args.valid), output_dir / 'valid', corpus_dir)
    if args.test:
        write(Path(args.test), output_dir / 'test', corpus_dir)


def write(id_file: Path, output_dir: Path, input_dir: Path):
    output_dir.mkdir(exist_ok=True)
    with id_file.open() as f:
        for line in f:
            doc_id = line.strip()
            files = list(input_dir.glob(f'**/{doc_id}.knp'))
            if not files:
                print(f'Cannot copy \'{doc_id}.knp\': No such file in {input_dir}', file=sys.stderr)
                continue
            file = files[0]
            shutil.copy(str(file), str(output_dir))
            print(f'copy {file} to {output_dir}')


if __name__ == '__main__':
    main()
