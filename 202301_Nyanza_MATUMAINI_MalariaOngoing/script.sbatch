#!/bin/bash

#SBATCH --nodes=1

#SBATCH --ntasks-per-node=1

#SBATCH --cpus-per-task=1

#SBATCH --time=05-00:00:00
#SBATCH --partition=cpu_medium
#SBATCH --mem=8GB

#SBATCH --job-name=CROI_EMOD
#SBATCH --chdir=/gpfs/data/bershteynlab/EMOD/citrod01/MATUMAINI/202301_Nyanza_MATUMAINI_MalariaOngoing

#SBATCH --mail-type=END

#SBATCH --mail-user=daniel.citron@nyulangone.org

#SBATCH --output=/gpfs/data/bershteynlab/EMOD/citrod01/MATUMAINI/202301_Nyanza_MATUMAINI_MalariaOngoing/slurm_%j.out

# python optim_script.py

python run_scenarios.py -c optim_script.py --resample-method provided --samples resampled_parameter_sets.csv --output-dir croi_3 --suite-name croi_3 --table scenarios.csv