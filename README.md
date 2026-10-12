# Reference Genome Download and BLAST Database Pipeline

This pipeline downloads genome assemblies selected from the NCBI Genome website, organizes the genome FASTA files by taxonomic order and genus, and builds one nucleotide BLAST database per genome.

The user supplies:

1. An NCBI genome-table TSV file.
2. The taxonomic order to use as the parent output directory.

## Project structure

```text
genome_downloader/
├── input/
│   └──  genomes.tsv
│
├── output/
│   ├── logs/
│   ├── runs/
│   ├── genomes/
│   └── blast_db/
│
├── scripts/
│   ├── download_ref_genomes.slurm
│   ├── genome_pipeline.py
│   └── build_blast_dbs.py
│
├── environment.yml
└── README.md
```

## Requirements

The cluster must provide:

- SLURM
- Miniforge/Conda
- `unzip`

The Conda environment defined in `environment.yml` provides:

- Python 3
- NCBI Datasets CLI
- NCBI BLAST+

## Environment setup

The environment only needs to be created once. Run these setup commands from the cluster login/head node.

### 1. Load Miniforge

```bash
module load miniforge/25.9
```

### 2. Create the environment

From the project root:

```bash
conda env create -f environment.yml
```

This creates:

```text
genome_downloader
```

### 3. Activate the environment

```bash
conda activate genome_downloader
```

## Running the pipeline

From the project root:

### 1. Input TSV:

Download a genome table from the NCBI Genome website as a TSV file and place it in `input/`.

Example:

```text
input/bat_genomes.tsv
```

### 2. Submit slurm script
```bash
sbatch scripts/download_ref_genomes.slurm <tsv_filename> <phylogenetic_Order>
```

#### Example:

```bash
sbatch scripts/download_ref_genomes.slurm bat_genomes.tsv Chiroptera
```
--- 

#### NOTE:
The script automatically looks for:

```text
input/bat_genomes.tsv
```

The order argument becomes the parent directory under both:

```text
output/genomes/
output/blast_db/
```

The script automatically looks for:

```text
input/bat_genomes.tsv
```

The order argument becomes the parent directory under both:

```text
output/genomes/
output/blast_db/
```


## Workflow

```text
input/bat_genomes.tsv
        |
        v
genome_pipeline.py accessions
        |
        v
NCBI Datasets download + rehydrate
        |
        v
genome_pipeline.py sort
        |
        +--> output/runs/<name>_<jobid>/genome_manifest.tsv
        |
        v
output/genomes/Order/Genus/Genus_species_accession.fna
        |
        v
build_blast_dbs.py
        |
        v
output/blast_db/Order/Genus/
        |
        v
temporary download data removed
```

### 1. Extract assembly accessions

`genome_pipeline.py` locates the assembly accession column from the TSV input file and extracts unique accessions:

```text
GCF_#########.#
GCA_#########.#
```

### 2. Download and rehydrate genomes

The SLURM script passes the accession file to `NCBI Datasets`:

```bash
datasets download genome accession \
    --inputfile accessions.txt \
    --include genome \
    --dehydrated \
    --filename genomes.zip
```

The package is extracted and rehydrated:

```bash
datasets rehydrate --directory <dataset_directory>
```

### 3. Sort and rename genome FASTAs

`genome_pipeline.py` reads `assembly_data_report.jsonl`, determines genus and species, and moves each genome to:

```text
output/genomes/Order/Genus/Genus_species_accession.fna
```

Example:

```text
output/genomes/Chiroptera/Myotis/Myotis_lucifugus_GCF_000147115.1.fna
```

Existing genome files are not overwritten.

### 4. Build BLAST databases

`build_blast_dbs.py` reads the current run manifest and creates one nucleotide BLAST database per genome.

BLAST databases are stored under:

```text
output/blast_db/Order/Genus/
```

Example:

```text
output/blast_db/Chiroptera/Myotis/Myotis_lucifugus_GCF_000147115.1.*
```

Existing BLAST databases are skipped rather than rebuilt.

### 5. Cleanup

After all previous steps succeed, the SLURM script removes:

- `accessions.txt`
- `genomes.zip`
- the rehydrated NCBI download directory

The manifest is retained.

## Final Output Structure Example

```text
genome_downloader/
├── input/
│   ├── user1_bats.tsv
│   ├── user2_bats.tsv
│   └── ...
│
├── output/
│   ├── logs/
│   │   ├── genome_downloader_<jobid>.out
│   │   └── genome_downloader_<jobid>.out
│   │
│   ├── runs/
│   │   ├── user1_bats_<jobid>/
│   │   │   └── genome_manifest.tsv
│   │   └── user2_bats_<jobid>/
│   │       └── genome_manifest.tsv
│   │
│   ├── genomes/
│   │   └── Chiroptera/
│   │       ├── Myotis/
│   │       │   └── Myotis_lucifugus_GCF_000147115.1.fna
│   │       └── Pteropus/
│   │           └── Pteropus_vampyrus_GCF_123456789.1.fna
│   │
│   └── blast_db/
│       └── Chiroptera/
│           ├── Myotis/
│           │   └── Myotis_lucifugus_GCF_000147115.1.*
│           └── Pteropus/
│               └── Pteropus_vampyrus_GCF_123456789.1.*
│
├── scripts/
│   ├── download_ref_genomes.slurm
│   ├── genome_pipeline.py
│   └── build_blast_dbs.py
│
├── environment.yml
└── README.md
```

## Run Manifest

Every submitted job gets a unique run directory:

```text
output/runs/<tsv_name>_<jobid>/
```

Example:

```text
output/runs/bat_genomes_123456/
└── genome_manifest.tsv
```

The manifest contains:

- `accession`
- `organism`
- `genus`
- `species`
- `status`
- `output_fasta`

Possible status values:

- `added` — genome added during this run.
- `existing` — genome was already present in the shared collection.
- `missing_fasta` — the downloaded package did not contain a genome FASTA.

This keeps each run traceable even when several users contribute to the same shared genome collection.


## Multi-user example

Two users can place different TSV files in `input/`:

```text
input/
├── insectivorous_bats.tsv
└── fruit_bats.tsv
```

Then submit them independently:

```bash
sbatch scripts/download_ref_genomes.slurm insectivorous_bats.tsv Chiroptera
sbatch scripts/download_ref_genomes.slurm fruit_bats.tsv Chiroptera
```

Both jobs add genomes to the shared collections:

```text
output/genomes/Chiroptera/
output/blast_db/Chiroptera/
```

while retaining separate provenance:

```text
output/runs/insectivorous_bats_<jobid>/genome_manifest.tsv
output/runs/fruit_bats_<jobid>/genome_manifest.tsv
```

and separate logs:

```text
output/logs/genome_downloader_<jobid>.out
```
