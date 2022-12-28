import sys
import shutil
import argparse
from pathlib import Path
from typing import Dict

from kyoto_reader import KyotoReader


def configure(args: argparse.Namespace):
    """Create Makefile to preprocess corpus documents."""
    scripts_dir = Path(__file__).parent / 'scripts'
    makefile_path = Path(args.makefile_dir or args.data_dir) / args.makefile_name
    with scripts_dir.joinpath('template.mk').open() as f:
        string = f.read()
    with makefile_path.open('w') as f:
        f.write(string.format(in_dir=args.corpus_dir,
                              out_dir=args.data_dir,
                              juman_dic_dir=args.juman_dic_dir,
                              scripts_base_dir=scripts_dir,
                              knp=args.knp,
                              python=sys.executable))
    print(f'created {makefile_path.name} at {makefile_path.parent}')


def show(args: argparse.Namespace):
    """Show the specified document in a tree format."""
    reader = KyotoReader(args.path, target_cases=args.cases)
    for document in reader.process_all_documents():
        document.draw_tree()


def list_(args: argparse.Namespace):
    """List document IDs which specified path contains."""
    reader = KyotoReader(args.path)
    print('\n'.join(reader.doc_ids))


def idsplit(args: argparse.Namespace):
    """Copy files in a corpus to train, valid (dev), and test directory referring to ID files."""

    corpus_dir = Path(args.corpus_dir)
    output_dir = Path(args.output_dir)

    if args.dev and args.valid:
        print('Specify either --dev or --valid', file=sys.stderr)
        exit(1)

    def write(id_file: Path, out_dir: Path, name2path: Dict[str, Path]):
        out_dir.mkdir(exist_ok=True)
        with id_file.open() as f:
            for line in f:
                doc_id = line.strip()
                file_name = f'{doc_id}.knp'
                if file_name not in name2path:
                    print(f'Cannot copy \'{file_name}\': No such file in {corpus_dir}', file=sys.stderr)
                    continue
                print(f'copy {name2path[file_name]} to {out_dir}')
                shutil.copy(str(name2path[file_name]), str(out_dir))

    knp_files = {p.name: p for p in corpus_dir.glob('**/*.knp')}

    if args.train:
        write(Path(args.train), output_dir / 'train', knp_files)
    if args.dev:
        write(Path(args.dev), output_dir / 'dev', knp_files)
    if args.valid:
        write(Path(args.valid), output_dir / 'valid', knp_files)
    if args.test:
        write(Path(args.test), output_dir / 'test', knp_files)


def main():
    """Entry point of CLI commands."""
    parser = argparse.ArgumentParser(prog='kyoto', description='provide commands to process kyoto corpus')
    subparsers = parser.add_subparsers()

    # subcommand: configure
    parser_conf = subparsers.add_parser('configure', help='create Makefile for corpus preprocessing')
    parser_conf.add_argument('--corpus-dir', '-c', required=True, type=str,
                             help='path to directory where downloaded corpus files exist')
    parser_conf.add_argument('--data-dir', '-d', required=True, type=str,
                             help='path to directory where processed files will be saved')
    parser_conf.add_argument('--juman-dic-dir', required=True, type=str,
                             help='path to directory where JumanDIC files exist')
    parser_conf.add_argument('--makefile-dir', default=None, type=str,
                             help='path to directory where Makefile will be created (default: same as --data-dir)')
    parser_conf.add_argument('--makefile-name', default='Makefile', type=str,
                             help='name of makefile to be created (default: Makefile)')
    parser_conf.add_argument('--knp', default=shutil.which('knp'), type=str,
                             help='path to knp (default: follow PATH environment variable)')
    parser_conf.set_defaults(handler=configure)

    # subcommand: show
    parser_show = subparsers.add_parser('show', help='show corpus content in a tree format')
    parser_show.add_argument('path', type=str, help='path to input knp file or directory')
    parser_show.add_argument('--cases', type=str, nargs='*', default=None,
                             help='target cases separated by " " (default: all cases)')
    parser_show.set_defaults(handler=show)

    # subcommand: list/ls
    parser_list = subparsers.add_parser('list', aliases=['ls'], help='list document IDs')
    parser_list.add_argument('path', type=str, help='path to input knp file or directory')
    parser_list.set_defaults(handler=list_)

    # subcommand: idsplit
    parser_idsplit = subparsers.add_parser('idsplit', help='split corpus following ID files')
    parser_idsplit.add_argument('--corpus-dir', '-c', required=True, type=str,
                                help='path to directory where all corpus files exist')
    parser_idsplit.add_argument('--output-dir', '-o', required=True, type=str,
                                help='path to directory where copied files will be saved')
    parser_idsplit.add_argument('--train', default=None, type=str,
                                help='path to train id file')
    parser_idsplit.add_argument('--dev', default=None, type=str,
                                help='path to dev id file')
    parser_idsplit.add_argument('--valid', default=None, type=str,
                                help='path to valid id file')
    parser_idsplit.add_argument('--test', default=None, type=str,
                                help='path to test id file')
    parser_idsplit.set_defaults(handler=idsplit)

    args = parser.parse_args()
    args.handler(args)


if __name__ == '__main__':
    main()
