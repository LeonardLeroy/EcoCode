from __future__ import annotations


def main() -> None:
    total = 0
    for value in range(5000):
        total += (value * value) % 17
    print(total)


if __name__ == "__main__":
    main()
