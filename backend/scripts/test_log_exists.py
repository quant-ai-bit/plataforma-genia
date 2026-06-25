import os

def main():
    print("Files in backend:")
    for r, d, fs in os.walk('.'):
        for f in fs:
            if 'debug' in f or 'log' in f:
                print(os.path.join(r, f))

if __name__ == '__main__':
    main()
