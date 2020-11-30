import argparse

from kyoto_reader import KyotoReader


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_path', type=str, help='path to input knp file or directory')
    args = parser.parse_args()

    reader = KyotoReader(args.input_path)
    for document in reader.process_all_documents():
        document.draw_tree()


if __name__ == '__main__':
    main()
