from __future__ import annotations


def main() -> None:
    values = [index for index in range(2000)]
    transformed = [item * 3 - 7 for item in values]
    print(sum(transformed))


if __name__ == "__main__":
    main()
