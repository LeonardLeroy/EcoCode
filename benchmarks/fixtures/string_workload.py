from __future__ import annotations


def main() -> None:
    chunks: list[str] = []
    for index in range(1500):
        chunks.append(f"eco-{index:04d}")
    merged = "|".join(chunks)
    print(len(merged))


if __name__ == "__main__":
    main()
