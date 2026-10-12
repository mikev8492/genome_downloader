#!/usr/bin/env python3

import argparse
import csv
import json
import re
import shutil
from pathlib import Path


ACCESSION_PATTERN = re.compile(r"GC[AF]_\d+(?:\.\d+)?")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prepare and organize NCBI genome datasets."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    accession_parser = subparsers.add_parser(
        "accessions",
        help="Extract assembly accessions from an NCBI genome TSV."
    )
    accession_parser.add_argument("--tsv", type=Path, required=True)
    accession_parser.add_argument("--output", type=Path, required=True)

    sort_parser = subparsers.add_parser(
        "sort",
        help="Sort rehydrated genomes into genus folders."
    )
    sort_parser.add_argument("--dataset", type=Path, required=True)
    sort_parser.add_argument("--output", type=Path, required=True)
    sort_parser.add_argument("--manifest", type=Path, required=True)

    return parser.parse_args()


def extract_accessions(tsv_file, output_file):
    """Extract unique GCF/GCA assembly accessions from an NCBI TSV."""
    with tsv_file.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")

        if not reader.fieldnames:
            raise ValueError("TSV file has no header.")

        column = next(
            (
                field for field in reader.fieldnames
                if "assembly" in field.lower()
                and "accession" in field.lower()
            ),
            None
        )

        if column is None:
            raise ValueError("Assembly Accession column not found.")

        accessions = {
            match.group()
            for row in reader
            if (match := ACCESSION_PATTERN.search(row.get(column, "") or ""))
        }

    if not accessions:
        raise ValueError("No GCF_/GCA_ assembly accessions found.")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(sorted(accessions)) + "\n")

    print(f"Found {len(accessions)} unique genome accessions.")


def parse_taxonomy(organism):
    """Return filesystem-safe genus and species names."""
    parts = organism.split()

    if len(parts) < 2:
        return None

    genus, species = parts[:2]
    clean = lambda name: re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return clean(genus), clean(species)


def find_fasta(accession_dir):
    """Find the genomic FASTA for one assembly."""
    fastas = list(accession_dir.rglob("*.fna"))

    if not fastas:
        return None

    genomic = [fasta for fasta in fastas if "genomic" in fasta.name.lower()]
    return genomic[0] if genomic else fastas[0]


def read_metadata(report):
    """Yield accession, organism, genus, and species from NCBI metadata."""
    with report.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue

            record = json.loads(line)
            accession = record.get("accession")
            organism = record.get("organism", {}).get("organismName", "")
            taxonomy = parse_taxonomy(organism)

            if accession and taxonomy:
                yield accession, organism, *taxonomy


def sort_genomes(dataset, output):
    """Move genomes to Order/Genus/Genus_species_accession.fna."""
    data_dir = dataset / "ncbi_dataset" / "data"
    report = data_dir / "assembly_data_report.jsonl"

    if not report.exists():
        raise FileNotFoundError(f"Metadata report not found: {report}")

    rows = []

    for accession, organism, genus, species in read_metadata(report):
        source = find_fasta(data_dir / accession)
        destination = output / genus / f"{genus}_{species}_{accession}.fna"

        if source is None:
            status = "missing_fasta"
            output_fasta = ""
            print(f"WARNING: No FASTA found for {accession}")
        elif destination.exists():
            status = "existing"
            output_fasta = str(destination)
            print(f"Already exists: {destination}")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            status = "added"
            output_fasta = str(destination)
            print(f"{accession}: {organism} -> {destination}")

        rows.append({
            "accession": accession,
            "organism": organism,
            "genus": genus,
            "species": species,
            "status": status,
            "output_fasta": output_fasta,
        })

    return rows


def write_manifest(rows, path):
    """Write a TSV manifest of final genome paths."""
    fields = ["accession", "organism", "genus", "species", "status", "output_fasta"]

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_args()

    if args.command == "accessions":
        extract_accessions(args.tsv, args.output)
    else:
        rows = sort_genomes(args.dataset, args.output)
        write_manifest(rows, args.manifest)


if __name__ == "__main__":
    main()
