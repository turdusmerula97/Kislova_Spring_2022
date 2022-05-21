# *In silico* modeling of coverage profiles for multiplex target panels

### Authors
Anastasia Kislova
Ivan Pyankov (Supervisor)

## Environment
- Ubuntu 18.04 and remote server (Ubuntu 20.04)
- virtualenv 20.14.1
- Python 2.7.18
### Data sources

All primer sequences and lab results are the property of ParSeq Lab and are strictly private.

Reference sequences (as CFTR gene nucleotide sequence, chromosome 7 sequence, CFTR pseudogenes and others) belong to GRCh37 Human genome assembly and are taken from open sources:
- https://www.ncbi.nlm.nih.gov/genome/
- https://grch37.ensembl.org/index.html

## Introduction

The development of multiplex target panels for polymerase chain reaction means that highly specific primers are designed to minimize the number of amplicons for target regions. The panels are obligatory *in vitro* validated, but *in silico* validation would improve the existing pipeline.

The goal of this project was to test existing tool called *DegenPrimer* and try to adjust it for *in silico* validation  of designed target panels and check the output correlation with the real data


## Tool
DegenPrimer, developed in 2015 by Evgeniy Taranov, performs sophisticated analysis of degenerate primers, including:
- calculation of melting temperatures; 
- prediction of stable secondary structures and primer dimers; 
- cycle-by-cycle PCR simulation with any number or primers and matrices; 
- primer specificity checks with automated BLAST queries and consequent PCR simulation using BLAST results as matrices; 
- simulation of electrophoresis; and automated optimization of PCR conditions.

![DegenPrimer workflow](https://github.com/turdusmerula97/picturesBI22/blob/main/DegenPrimer-algorithm-en.png)

Aside from the sequences of the primers, matrices, and PCR conditions (such as Na + and Mg 2+ concentrations) PCR simulation takes into account concentrations of secondary structures, primer dimers, all annealing sites and alternative annealing conformations with mismatches, predicting not only the probable products but also their yields.

All predictions are based on the thermodynamics of the reaction system. Gibbs energies of annealing reactions are calculated using the nearest-neighbor model of the stability of oligonucleotide duplexes with mismatches.

Each analysis produces several reports that help to identify different problems that may be caused by some primers and primer combinations and select the best options available.

DegenPrimer is written in Python for Linux and is licensed under GPLv3. Most calculations are highly parallelized, so DegenPrimer benefits from multi-core CPUs. The main program has command line interface and is useful for batch analysis and scripting.

## Main tasks

1. Launch the tool (via virtual environment, solve some code issues and convert our data in suitable format).

3. Run the tool using different references (amplicons, gene, chromosome, sequences with pseudogenes), parameters, including comparison between the results of built in aligning mechanism and BLAST queries.

5. Compare the PCR products predictions of the tool with the real lab data and check if there is correlation between products concentrations and amplicons coverage profiles.


## Launch parameters

The main command to run DegenPrimer looked like this:
```bash
./degen_primer ./primers_master.cfg --Mg float --dNTP float --DNA float --max-amplicon int --max-mismatches int --analyse-all-annealings True --polymerase float --cycles int --template-files ./sequence.fasta
```
Here the primers sequences, ids and concentrations are merged into the .cfg file. 
The concentrations of electrolytes, DNA, maximum and minimum amplicon size, maximum possible mismatches during annealing sites search, number of PCR simulation cycles and others are chosen individually.
The reference sequence is given as the file in .fasta format.

The other option is to use BLAST queries instead of built-in alignment mechanism. The command for this is given below:
```bash
./degen_primer ./primers_master.cfg --do-blast True --organisms Human --Mg float --dNTP float --DNA float --max-amplicon int --max-mismatches int --analyse-all-annealings True --polymerase float --cycles int
```
So the BLAST mode is on and its possible to restrict the search area to the single organism or a group of organisms.

The .cfg file looks like this:

![Primers](https://github.com/turdusmerula97/picturesBI22/blob/main/primers.jpeg)

We used the same parameters as in the lab process.

## Work process

The DegenPrimer was initially developed to use on small proceryotic genomes and small amount of primers. So to use it on the pool of dozens of primers and long reference sequences (as chromosome) we needed to launch it via remote server with 40 Gb RAM and do some small code refactoring. 

We succesively launched the tool on two pools of primers and an amplicons sequence, gene (CFTR) and chromosome (chr 7). Also we added the pseudogene sequence from chr 20 to check if the tool will find an annealing sites on it. 

To primarily check the accuracy of tool alignment mechanism and search engine we launched the tool also using BLAST queries to NCBI database. 

Then we compared the results of the DegenPrimer predictions with our real lab data (found amplicons and correlation between the concentrations of the products and the amplicons coverage profiles). Unfortunately, the real concentrations of our primers were extremely big for the DegenPrimer so to avoid the quick and full saturation of the system during PCR simulation we needed to reduce the concentrations in 100 times.

## Results

We obtained predictions of possible PCR products and their concentrations.

![Predicted products and their concentrations](https://github.com/turdusmerula97/picturesBI22/blob/main/image_2022-05-21_23-28-39.png)

![Electronogram of the possible products](https://github.com/turdusmerula97/picturesBI22/blob/main/image_2022-05-21_23-28-08.png)

The predicted primers duplexes and PCR products did not fully match the real lab data - DegenPrimer have found some non-existing duplexes and amplicons and have not found some of the existing ones - the accuracy of the predictions varied from 60 to 75%.

While using real primers concentrations for the analysis, the tool predicted quick and full saturation of the system, which is not confirmed by the lab data. To get amount of products to check the correlation, we needed to reduce the concentrations of primers in 100 times.

We did not find any correlation between the predicted product concentrations and amplicons coverage profiles. The average Pearson correlation coefficient for the pools of primers was 0.095.

![The example of the comparison between the possible products concentrations and the coverage profiles of the real amplicons](https://github.com/turdusmerula97/picturesBI22/blob/main/image_2022-05-21_23-27-45.png)

## Conclusion
Due to the fact that the results, obtained by DegenPrimer, were not fully matching the real data from the lab (annealing sites, duplexes and possible products) and predicted PCR concentrations did not correlate with the amplicons coverage profiles, it was decided that this tool is not suitable for *in silico* validation of the multiplex target panels



## References

The original author of the DegenPrimer is Evgeniy Taranov https://github.com/allista
