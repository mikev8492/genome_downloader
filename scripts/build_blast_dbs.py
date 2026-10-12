#!/usr/bin/env python3

import argparse
import csv
import subprocess
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create one nucleotide BLAST database per genome."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Genome manifest produced by genome_pipeline.py."
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Parent directory for BLAST databases."
    )
    return parser.parse_args()


def read_genomes(manifest):
    with manifest.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            fasta = row.get("output_fasta", "").strip()
            if fasta:
                yield Path(fasta)


def blast_db_exists(prefix):
    return any(
        Path(str(prefix) + suffix).exists()
        for suffix in (".nhr", ".nin", ".nsq", ".ndb")
    )


def build_blast_db(genome, output_dir):
    genus = genome.parent.name
    db_dir = output_dir / genus
    db_dir.mkdir(parents=True, exist_ok=True)
    db_prefix = db_dir / genome.stem

    if blast_db_exists(db_prefix):
        print(f"BLAST DB already exists: {db_prefix}")
        return

    subprocess.run(
        [
            "makeblastdb",
            "-in", str(genome),
            "-dbtype", "nucl",
            "-parse_seqids",
            "-title", genome.stem,
            "-out", str(db_prefix),
        ],
        check=True,
    )

    print(f"Built BLAST DB: {db_prefix}")


def main():
    args = parse_args()
    genomes = list(read_genomes(args.manifest))

    if not genomes:
        raise SystemExit(f"No genome paths found in manifest: {args.manifest}")

    print(f"Processing {len(genomes)} genome databases.")

    for genome in genomes:
        if genome.exists():
            build_blast_db(genome, args.output)
        else:
            print(f"WARNING: Genome file not found: {genome}")


if __name__ == "__main__":
    main()
