## OSS-Bench: Benchmark Generator for Coding LLMs

*Beta — Development Ongoing*

**Contact:** yuancheng@comp.nus.edu.sg

OSS-Bench automatically constructs large-scale, live evaluation tasks from real-world open-source software. It replaces individual functions in mature projects with LLM-generated code and evaluates them against three natural metrics:

1. **Compilability** — does the code compile?
2. **Functional correctness** — does it pass the project’s test suite?
3. **Memory safety** — are there sanitizer-reported errors?

Failed compilations, test-suite violations, or sanitizer alerts serve as reliable ground truth for problematic code.

---

### Prerequisites

- **Operating System:** Ubuntu (tested on 20.04+)
- **Docker:** to instantiate the OSS environment and run evaluations  
  ```bash
  sudo apt update
  sudo apt install docker.io

* **Python 3.8+** with:

  ```bash
  pip install tqdm sqlite3
  ```

---

### Docker Images

Pull the prebuilt images for your target OSS:

```bash
# For PHP
docker pull 0599jiangyc/flowfusion4llm:latest

# For SQLite
docker pull 0599jiangyc/sqlite4llm:latest
```

---

### Getting Started

1. **Extract functions**
   Use `function.py` to extract C functions from the OSS codebase:

   ```bash
   python3 function.py --oss php-src
   ```

   * The extracted PHP functions will be saved to `./data/php-src/function.db`.
   * Example LLM outputs (GPT-O1) are in `./data/php-src/gpt-o1-seed0/function.db`.

2. **Collect LLM outputs**
   Use `llm.py` (with Ollama APIs) to generate candidate implementations:

   ```bash
   python3 llm.py --model gpt-o1-seed0 --oss php-src
   ```

3. **Evaluate compilability**

   ```bash
   python3 main.py \
     --model gpt-o1-seed0 \
     --oss php-src \
     --linear-execution
   ```

4. **Evaluate functionality & memory safety**
   First, generate the dataset:

   ```bash
   python3 main.py \
     --model gpt-o1-seed0 \
     --oss php-src \
     --dataset-generation
   ```

   After 3–5 iterations (to build up the test dataset), run:

   ```bash
   python3 main.py \
     --model gpt-o1-seed0 \
     --oss php-src \
     --test
   ```

5. **Compute scores**

   ```bash
   python3 score.py
   ```

---

Happy benchmarking! 🚀