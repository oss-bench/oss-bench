## OSS-Bench: Benchmark Generator for Coding LLMs

**(Beta - Development Ongoing)**

*Contact me: yuancheng@comp.nus.edu.sg*

**OSS-BENCH, a benchmark generator that automatically constructs large-scale, live evaluation tasks from real-world open-source software. OSS-BENCH replaces individual functions from mature open-source projects with LLM outputs against three natural metrics—compilability, functional test, and memory safety—using reliable ground truth: failed compilations, test-suite violations, or sanitizer alerts indicate problematic code.**

#### Prerequasites

System: Ubuntu

OSS-Bench requires docker to instantite OSS and evaluate LLMs:

```bash
apt install docker.io
```

Pull pre-build docker images for your need:

```bash
docker pull 0599jiangyc/flowfusion4llm:latest # OSS = PHP
docker pull 0599jiangyc/sqlite4llm:latest # OSS = SQLite
```

Python libraries:

```bash
pip install tqdm
pip install sqlite3
```

#### Instructions

You can use function.py to extract C functions from OSS

You can use llm.py to collect LLMs output (ollama APIs).

The extracted function for PHP is ready at ./data/php-src/function.db

The example LLM output for GPT-O1 is at ./data/php-src/gpt-o1-seed0/function.db

*Step 1: Evaluating Compilability*

```bash
python3 main.py --model gpt-o1-seed0 --OSS php-src --linear-execution
```

*Step 2: Evaluating Functionality and Memory Safety*

```bash
python3 main.py --model gpt-o1-seed0 --OSS php-src --dataset-generation
```

open another shell, after 3-5 iterations ready for the dataset, then start

```bash
python3 main.py --model gpt-o1-seed0 --OSS php-src --test
```

*Step 3: Scoring*

```bash
python3 score.py
```

