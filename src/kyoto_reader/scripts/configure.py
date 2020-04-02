import sys
import shutil
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
    parser.add_argument('--makefile-dir', default=None, type=str,
                        help='path to directory where Makefile will be created (default: same as --data-dir)')
    parser.add_argument('--makefile-name', default='Makefile', type=str,
                        help='name of makefile to be created')
    parser.add_argument('--knp', default=shutil.which('knp'), type=str,
                        help='path to knp')
    args = parser.parse_args()

    here = Path(__file__).parent
    makefile_dir = args.makefile_dir if args.makefile_dir else args.data_dir
    makefile_path = Path(makefile_dir) / args.makefile_name
    with here.joinpath('template.mk').open() as f:
        string = f.read()
    with makefile_path.open('w') as f:
        f.write(string.format(in_dir=args.corpus_dir,
                              out_dir=args.data_dir,
                              juman_dic_dir=args.juman_dic_dir,
                              scripts_base_dir=here,
                              knp=args.knp,
                              python=sys.executable))
    print(f'created {makefile_path.name} at {makefile_path.parent}')


if __name__ == '__main__':
    main()
