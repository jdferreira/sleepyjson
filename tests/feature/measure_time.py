from sleepyjson import Reader
from json_generator import generate_big_json

FILENAME = 'tmp.json'

def main():
    generate_big_json(FILENAME)

    with open(FILENAME) as f:
        reader = Reader(f)

        print(f'Length of JSON object: {len(reader)}')

if __name__ == '__main__':
    main()
