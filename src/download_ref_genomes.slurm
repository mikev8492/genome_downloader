#!/bin/bash
#SBATCH --partition=Orion
#SBATCH --job-name=genome_downloader
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=12:00:00
#SBATCH --mem=8G
#SBATCH --output=output/logs/genome_downloader_%j.out
#SBATCH --error=output/logs/genome_downloader_%j.out

set -euo pipefail

# Usage:
#   sbatch src/download_ref_genomes.slurm bat_genomes.tsv Chiroptera
#
# Place the TSV file in input/ before submitting the job.

if [[ $# -ne 2 ]]; then
    echo "Usage: sbatch src/download_ref_genomes.slurm <genomes.tsv> <order>"
    exit 1
fi

PROJECT_DIR="${SLURM_SUBMIT_DIR:-$PWD}"
TSV_FILE="$PROJECT_DIR/input/$1"
ORDER="${2// /_}"

GENOME_SCRIPT="$PROJECT_DIR/src/genome_pipeline.py"
BLAST_SCRIPT="$PROJECT_DIR/src/build_blast_dbs.py"

NAME="$(basename "$TSV_FILE")"
NAME="${NAME%.*}"
RUN_NAME="${NAME}_${SLURM_JOB_ID}"

RUN_DIR="$PROJECT_DIR/output/runs/$RUN_NAME"
ACCESSIONS="$RUN_DIR/accessions.txt"
ZIP_FILE="$RUN_DIR/genomes.zip"
DATASET_DIR="$RUN_DIR/ncbi_genomes"
MANIFEST="$RUN_DIR/genome_manifest.tsv"

GENOME_DIR="$PROJECT_DIR/output/genomes/$ORDER"
BLAST_DIR="$PROJECT_DIR/output/blast_db/$ORDER"

[[ -f "$TSV_FILE" ]] || { echo "ERROR: TSV not found: $TSV_FILE"; exit 1; }
[[ -f "$GENOME_SCRIPT" ]] || { echo "ERROR: Script not found: $GENOME_SCRIPT"; exit 1; }
[[ -f "$BLAST_SCRIPT" ]] || { echo "ERROR: Script not found: $BLAST_SCRIPT"; exit 1; }

mkdir -p "$RUN_DIR" "$GENOME_DIR" "$BLAST_DIR"

module load miniforge/25.9
eval "$(conda shell.bash hook)"
conda activate genome_downloader

command -v datasets >/dev/null 2>&1 || {
    echo "ERROR: datasets not found."
    exit 1
}

command -v makeblastdb >/dev/null 2>&1 || {
    echo "ERROR: makeblastdb not found."
    exit 1
}

echo "======================================================"
echo "Genome Downloader"
echo "======================================================"
echo "Job ID     : $SLURM_JOB_ID"
echo "Input TSV  : $TSV_FILE"
echo "Order      : $ORDER"
echo "Run folder : $RUN_DIR"
echo "Start time : $(date)"
echo "======================================================"
echo

# 1. Extract assembly accessions
python "$GENOME_SCRIPT" accessions \
    --tsv "$TSV_FILE" \
    --output "$ACCESSIONS"

# 2. Download and rehydrate genomes
datasets download genome accession \
    --inputfile "$ACCESSIONS" \
    --include genome \
    --dehydrated \
    --filename "$ZIP_FILE"

mkdir -p "$DATASET_DIR"
unzip -q "$ZIP_FILE" -d "$DATASET_DIR"

datasets rehydrate \
    --directory "$DATASET_DIR"

# 3. Sort and rename genome FASTA files
python "$GENOME_SCRIPT" sort \
    --dataset "$DATASET_DIR" \
    --output "$GENOME_DIR" \
    --manifest "$MANIFEST"

# 4. Build BLAST databases for genomes in this run
python "$BLAST_SCRIPT" \
    --manifest "$MANIFEST" \
    --output "$BLAST_DIR"

# 5. Remove temporary files; keep the manifest
rm -rf "$DATASET_DIR"
rm -f "$ZIP_FILE" "$ACCESSIONS"

echo
echo "======================================================"
echo "Pipeline complete: $(date)"
echo "Genomes   : $GENOME_DIR"
echo "BLAST DBs : $BLAST_DIR"
echo "Manifest  : $MANIFEST"
echo "Log       : $PROJECT_DIR/output/logs/genome_downloader_${SLURM_JOB_ID}.out"
echo "======================================================"
