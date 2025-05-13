import os
import shutil
import ollama
from tqdm import tqdm
from sqlite3db import FunctionDB
from prompt import Prompt
import multiprocessing

# nothink = '//nothink'

class Backend:
    def __init__(self, seed=0):
        prompt = Prompt()
        self.system_prompt = prompt.system_prompt # + nothink
        self.optimizing_prompt = prompt.optimizing_prompt
        self.seed = seed

    def parse_llm_output(self, output):
        if "```" in output:
            try:
                output = output.split('```c')[1].split('```')[0]
                return output
            except:
                return output
        else:
            return output

    def _ollama_chat_process(self, return_queue, model, messages, options):
        """
        Helper function to be run in a separate process.
        Calls ollama.chat and places the result or exception into a queue.
        """
        try:
            response = ollama.chat(model=model, messages=messages, options=options)
            return_queue.put(("ok", response))
        except Exception as e:
            # Put the exception in the queue so we can handle it in the parent process
            return_queue.put(("error", e))

    def ollama_api(self, cfunction, model, timeout=120):
        """
        Enforce a timeout on the ollama.chat call by running it in a separate process.
        If it doesn’t finish within `timeout` seconds, it will be killed and a timeout
        message will be returned.
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.optimizing_prompt.format(cfunction=cfunction)},
        ]

        # Set up multiprocessing
        manager = multiprocessing.Manager()
        return_queue = manager.Queue()
        proc = multiprocessing.Process(
            target=self._ollama_chat_process,
            args=(return_queue, model, messages, {"seed": self.seed})
        )

        # Start the process and wait for the result
        proc.start()
        proc.join(timeout)

        # If it’s still alive after `timeout` seconds, kill it
        if proc.is_alive():
            proc.terminate()
            proc.join()
            return "Error: Timeout while waiting for ollama.chat response"

        # Now retrieve the result from the queue
        if not return_queue.empty():
            status, result = return_queue.get()
            if status == "error":
                # If an exception occurred in the child process, handle accordingly
                return f"Error: Exception in child process: {result}"
            else:
                # Parse the content from the response
                optimized_code = result["message"]["content"]
                return self.parse_llm_output(optimized_code)
        else:
            return "Error: No response received from ollama.chat"

    def run(self, oss, model, seed):
        label = f"{model.replace(':','-')}-seed{seed}"
        if not os.path.exists(f"./data/{oss}/{label}"):
            os.mkdir(f"./data/{oss}/{label}")
        db_path = f"./data/{oss}/{label}/function.db"
        if not os.path.exists(db_path):
            shutil.copy(f"./data/{oss}/function.db", db_path)

        db = FunctionDB(db_path)
        if oss=="php-src":
            maxx = 10534
        elif oss=="sqlite":
            maxx = 7321
        for idd in tqdm(range(0,maxx)):
            i, idx, filepath, token_number, function, todo_function = db.fetch_function_by_id(idd+1)
            if todo_function != '-':
                continue

            new_function = self.ollama_api(function, model, timeout=120)
            db.update_optimized_function(idx, new_function)

        db.close()

# Example usage
if __name__ == "__main__":
    llm_backend = Backend()
    # modify the following oss and model to collect LLMs output
    llm_backend.run(oss="sqlite", model="qwen2.5-coder:3b", seed=0)
