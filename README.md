## OSS-Bench: Benchmark Generator for Coding LLMs

A new release will be updated in June 2025 with various improvements. Stay tuned!

*Beta — Development Ongoing*

**Contact:** [yuancheng@comp.nus.edu.sg](mailto:yuancheng@comp.nus.edu.sg)

**OSS-Bench** automatically constructs large-scale, live evaluation tasks from real-world open-source software. It replaces individual functions in mature projects with LLM-generated code and evaluates them using three key metrics:

1. **Compilability** — Does the code compile?
2. **Functional Correctness** — Does it pass the project’s test suite?
3. **Memory Safety** — Are there sanitizer-reported errors?

Failed compilations, test-suite violations, and sanitizer alerts serve as reliable ground truth for identifying problematic code.

---

### Prerequisites

* **Operating System:** Ubuntu (tested on 20.04+)
* **Docker:** Required to instantiate the OSS environment and run evaluations

  ```bash
  sudo apt update
  sudo apt install docker.io
  ```
* **Python 3.8+** with:

  ```bash
  pip install tqdm sqlite3
  ```

---

### Docker Images

Pull the prebuilt Docker images for your target OSS:

```bash
# For PHP
docker pull 0599jiangyc/flowfusion4llm:latest

# For SQLite
docker pull 0599jiangyc/sqlite4llm:latest
```

---

### Getting Started with OSS-Bench (PHP)

#### 1. Extract Functions

We have pre-extracted C functions from the [php-src](https://github.com/php/php-src) repository at [this commit](https://github.com/php/php-src/commit/3786cff1f3f3d755f346ade78979976fee92bb48).

These are stored in `./data/php-src/function.db` with the following schema:

* `id` (INTEGER PRIMARY KEY AUTOINCREMENT): 1, 2, 3, ...
* `function_index` (TEXT, UNIQUE): `./php-src/main/output.c:77:20`
* `filepath` (TEXT): `./php-src/main/output.c`
* `token_number` (INT): Word count (e.g., 10)
* `original_function` (TEXT): Original function code
* `optimized_function` (TEXT): Initially `-`, to be filled with LLM output

#### 2. Collect LLM Outputs

* The default prompt is defined in `./prompt.py`.
* Use `./llm.py` to generate LLM outputs via the **Ollama** platform.
* Alternatively, use your own method:

  1. Create a new folder: `./data/php-src/{model-name}`
  2. Copy the database:

     ```bash
     cp ./data/php-src/function.db ./data/php-src/{model-name}/function.db
     ```
  3. Populate the `optimized_function` field in the copied DB with your LLM outputs.

#### 3. Evaluate Compilability

Run the compilability check for all generated functions:

```bash
python3 main.py \
  --model gpt-o1-seed0 \
  --oss php-src \
  --linear-execution
```

Replace `gpt-o1-seed0` with your model folder name in `./data/php-src`.

This step may take several hours. *(TODO: Add parallel execution support)*

Output includes:

* `invalid_functions`
* `linear_compile_fail_logs`
* `fuzzresults` (optional; if sanitizer alerts were triggered)

#### 4. Evaluate Functionality & Memory Safety

**Step 1:** In one terminal (or tmux session), run dataset generation:

```bash
python3 main.py \
  --model gpt-o1-seed0 \
  --oss php-src \
  --dataset-generation
```

This creates:

* `dataset.db`
* `patches/` directory in `./data/php-src/{model-name}/`

**Step 2:** In a second terminal, start the test execution:

```bash
python3 main.py \
  --model gpt-o1-seed0 \
  --oss php-src \
  --test
```

This produces:

* `testlog` in `./data/php-src/{model-name}/`

#### 5. Compute Final Scores

Run the scoring script to summarize results:

```bash
python3 score.py --model gpt-o1-seed0
```

---

**Happy benchmarking! 🚀**
