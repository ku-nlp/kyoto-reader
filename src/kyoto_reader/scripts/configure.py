import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--corpus-dir', '-c', required=True, type=str,
                        help='path to directory where downloaded corpus files exist')
    parser.add_argument('--data-dir', '-d', required=True, type=str,
                        help='path to directory where processed files will be saved')
    parser.add_argument('--juman-dic-dir', required=True, type=str,
                        help='path to directory where JumanDIC files exist')
    parser.add_argument('--makefile-name', default='corpus.mk', type=str,
                        help='name of makefile to be created')
    args = parser.parse_args()

    here = Path(__file__).parent
    with here.joinpath('template.mk').open() as f:
        string = f.read()
    with Path.cwd().joinpath(args.makefile_name).open('w') as f:
        f.write(string.format(in_dir=args.corpus_dir,
                              out_dir=args.data_dir,
                              juman_dic_dir=args.juman_dic_dir,
                              scripts_base_dir=here))


if __name__ == '__main__':
    main()
