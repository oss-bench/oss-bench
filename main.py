#!/usr/bin/env python3

import os
import argparse
import time
from tqdm import tqdm
from sqlite3db import FunctionDB, DatasetDB, TestResultDB, FuzzResultDB

# demonstration code for OSS(php)-Bench and OSS(sqlite)-Bench

class OSSBench:
    # OSS options = ["php-src", "sqlite"]
    def __init__(self, model, OSS):
        self.model = model
        self.OSS = OSS
        if self.OSS=="php-src":
            self.function_num = 10534 # functions in word count >=10 and <256
        elif self.OSS=="sqlite":
            self.function_num = 7321 # functions in word count >=10 and <256
        self.test_iteration_num = 1000 # how many iterations we need
        self.valid_functions = list(range(1, self.function_num+1))

    def replace_function(self, file_path, old, new):
        with open(file_path, 'r', encoding='iso-8859-1') as file:
            file_contents = file.read()
        updated_contents = file_contents.replace(old, new)
        with open(file_path, 'w', encoding='iso-8859-1') as file:
            file.write(updated_contents)

    # this function evaluates the metric I - compilability
    def linear_execution(self):

        make_nothing_functions = []
        make_nothing_function_file = f"./data/{self.OSS}/{self.model}/make_nothing_functions"

        if self.OSS=="php-src" and not os.path.exists(f"./data/php-src/php-src"):
            os.system("cd ./data/php-src/ && git clone https://github.com/php/php-src.git && cd php-src && git checkout 3786cff1f3f3d755f346ade78979976fee92bb48")

        if self.OSS=="sqlite" and not os.path.exists(f"./data/sqlite/sqlite"):
            os.system("cd ./data/sqlite/ && git clone https://github.com/sqlite/sqlite.git && cd sqlite && git checkout 942c9587698715734715242737dba07ef296b0ef")

        self.function_db = FunctionDB(f"./data/{self.OSS}/{self.model}/function.db")
        
        start_index = 0
        invalid_functions = []

        if os.path.exists(f"./data/{self.OSS}/{self.model}/invalid_functions"):
            print("linear execution skipped.")
            f = open(f"./data/{self.OSS}/{self.model}/invalid_functions", "r")
            invalid_functions = eval(f.read())
            f.close()
            self.valid_functions = list(set(self.valid_functions) - set(invalid_functions))
            start_index = invalid_functions[-1]
        
        for i in tqdm(range(start_index, len(self.valid_functions))):
            function_id = i+1
            while True:
                fid, function_index, filepath, token_number, old, new = self.function_db.fetch_function_by_id(function_id)
                if new!="-":
                    break
                else:
                    print("waiting for optimized function from LLM")
                    time.sleep(1)
            try:
                self.replace_function(f"./data/{self.OSS}/{filepath}", old, new)
            except:
                invalid_functions.append(function_id)
                f = open(f"./data/{self.OSS}/{self.model}/invalid_functions", "w")
                f.write(str(invalid_functions))
                f.close()
                continue
            
            os.system(f"cd ./data/{self.OSS}/{self.OSS} && git diff *.c > ./test.diff && git restore *.c")
            f = open(f"./data/{self.OSS}/{self.OSS}/test.diff", 'r', encoding="iso-8859-1")
            diff = f.read()
            f.close()

            docker_label = f"linear_{self.model}_{self.OSS}"

            try:
                os.system(f"docker kill {docker_label}")
            except:
                pass

            try:
                os.system(f"docker rm {docker_label}")
            except:
                pass
            
            if os.path.exists(f"/tmp/{docker_label}_make.log"):
                os.remove(f"/tmp/{docker_label}_make.log")

            if self.OSS=="php-src":
                os.system(f"docker run --name {docker_label} -dit 0599jiangyc/flowfusion4llm:latest bash")
                os.system(f"docker cp ./data/php-src/php-src/test.diff {docker_label}:/home/phpfuzz/WorkSpace/flowfusion/php-src/")
                os.system(f"docker exec -it {docker_label} bash -c 'cd /home/phpfuzz/WorkSpace/flowfusion/php-src/ && git apply ./test.diff && timeout 600 make -j16 > ./make.log 2>&1'")
                os.system(f"docker cp {docker_label}:/home/phpfuzz/WorkSpace/flowfusion/php-src/make.log /tmp/{docker_label}_make.log")
            elif self.OSS=="sqlite":
                os.system(f"docker run --name {docker_label} -dit 0599jiangyc/sqlite4llm:latest bash")
                os.system(f"docker cp ./data/sqlite/sqlite/test.diff {docker_label}:/home/test/sqlite/")
                os.system(f"docker exec -it {docker_label} bash -c 'su test -c \"cd /home/test/sqlite/ && git apply ./test.diff && cd build && timeout 600 make -j24 > ./make.log 2>&1\"'")
                os.system(f"docker cp {docker_label}:/home/test/sqlite/build/make.log /tmp/{docker_label}_make.log")
            else:
                print("unsupported OSS. abort...")
                exit()
      
            if not os.path.exists(f"/tmp/{docker_label}_make.log"):
                invalid_functions.append(function_id)
                f = open(f"./data/{self.OSS}/{self.model}/invalid_functions", "w")
                f.write(str(invalid_functions))
                f.close()
                continue

            f = open(f"/tmp/{docker_label}_make.log","r",encoding='iso-8859-1')
            compile_result = f.read()
            f.close()
            if "Sanitizer:" in compile_result:
                print("Sanitizer Alert!")
                invalid_functions.append(function_id)
                if not os.path.exists(f"./data/{self.OSS}/{self.model}/fuzzresults"):
                    os.mkdir(f"./data/{self.OSS}/{self.model}/fuzzresults")
                    if not os.path.exists(f"./data/{self.OSS}/{self.model}/fuzzresults/compilefails"):
                        os.mkdir(f"./data/{self.OSS}/{self.model}/fuzzresults/compilefails")
                f = open(f"./data/{self.OSS}/{self.model}/fuzzresults/compilefails/{function_id}.log", 'w', encoding="iso-8859-1")
                f.write(compile_result)
                f.close()
                f = open(f"./data/{self.OSS}/{self.model}/invalid_functions", "w")
                f.write(str(invalid_functions))
                f.close()
            # excluding non-affect functions
            elif (self.OSS=="php-src" and "libtool" not in compile_result) or (self.OSS=="sqlite" and "make: Nothing to be done for 'all'." in compile_result):            
                print("make nothing")
                make_nothing_functions.append(function_id)
                f = open(make_nothing_function_file, "w")
                f.write(str(make_nothing_functions))
                f.close()
            elif (self.OSS=="php-src" and "Build complete." not in compile_result) or (self.OSS=="sqlite" and "error: " in compile_result):
                if not os.path.exists(f"./data/{self.OSS}/{self.model}/linear_compile_fail_logs"):
                    os.mkdir(f"./data/{self.OSS}/{self.model}/linear_compile_fail_logs")
                print("FAILED!")
                invalid_functions.append(function_id)
                f = open(f"./data/{self.OSS}/{self.model}/invalid_functions", "w")
                f.write(str(invalid_functions))
                f.close()
                os.system(f"cp /tmp/{docker_label}_make.log ./data/{self.OSS}/{self.model}/linear_compile_fail_logs/{function_id}.log")
            else:
                print("PASSED!")
                continue

    def dataset_generation(self):

        one_percent = 73 if self.OSS=="sqlite" else 100

        self.function_db = FunctionDB(f"./data/{self.OSS}/{self.model}/function.db")
        import random
        random.seed(0)
        f = open(f"./data/{self.OSS}/{self.model}/invalid_functions", "r")
        invalid_functions = eval(f.read())
        f.close()
        self.valid_functions = list(set(self.valid_functions) - set(invalid_functions))

        valid_function_len = len(self.valid_functions)

        random_function_ids = []

        # prepare enough random index for dataset
        while not len(random_function_ids)>1000000:
            function_ids = list(range(0, valid_function_len))
            random.shuffle(function_ids)
            random_function_ids += function_ids

        self.dataset_db = DatasetDB(f"./data/{self.OSS}/{self.model}/dataset.db")

        function_id_index = -1

        current_iteration = 1

        while function_id_index<1000000:
            print("iteration:", current_iteration)

            function_patch_count = 0
            
            docker_label = f"datagen_{self.model}_{self.OSS}"
            
            patch_function_ids = []

            while function_patch_count<one_percent:
                function_id_index += 1
                function_patch_count += 1
                each_function_id = self.valid_functions[random_function_ids[function_id_index]]
                function_id, function_index, filepath, token_number, old, new = self.function_db.fetch_function_by_id(each_function_id)
                try:
                    self.replace_function(f"./data/{self.OSS}/{filepath}", old, new)
                except:
                    print("MISSED")
                    continue
                patch_function_ids.append(function_id)
            
            os.system(f"cd ./data/{self.OSS}/{self.OSS} && git diff *.c > ./test.diff && git restore *.c")
            f = open(f"./data/{self.OSS}/{self.OSS}/test.diff", 'r', encoding="iso-8859-1")
            diff = f.read()
            f.close()

            # kill docker 
            try:
                os.system(f"docker kill {docker_label}")
            except:
                pass

            try:
                os.system(f"docker rm {docker_label}")
            except:
                pass
            
            if os.path.exists(f"/tmp/{docker_label}_make.log"):
                os.remove(f"/tmp/{docker_label}_make.log")
            
            if self.OSS=="php-src":
                os.system(f"docker run --name {docker_label} -dit 0599jiangyc/flowfusion4llm:latest bash")
                os.system(f"docker cp ./data/php-src/php-src/test.diff {docker_label}:/home/phpfuzz/WorkSpace/flowfusion/php-src/")
                os.system(f"docker exec -it {docker_label} bash -c 'cd /home/phpfuzz/WorkSpace/flowfusion/php-src/ && git apply ./test.diff && timeout 600 make -j16 > ./make.log 2>&1'")
                os.system(f"docker cp {docker_label}:/home/phpfuzz/WorkSpace/flowfusion/php-src/make.log /tmp/{docker_label}_make.log")

                if not os.path.exists(f"/tmp/{docker_label}_make.log"):
                    print("patch error.. sometimes it happens... fix me")
                    continue

            elif self.OSS=="sqlite":
                os.system(f"docker run --name {docker_label} -dit 0599jiangyc/sqlite4llm:latest bash")
                os.system(f"docker cp ./data/sqlite/sqlite/test.diff {docker_label}:/home/test/sqlite/")
                os.system(f"docker exec -it {docker_label} bash -c 'su test -c \"cd /home/test/sqlite/ && git apply ./test.diff && cd build && timeout 600 make -j24 > ./make.log 2>&1\"'")
                os.system(f"docker cp {docker_label}:/home/test/sqlite/build/make.log /tmp/{docker_label}_make.log")

                if not os.path.exists(f"/tmp/{docker_label}_make.log"):
                    print("patch error.. sometimes it happens... fix me")
                    continue
                
            else:
                print("error")
                exit(0)

            f = open(f"/tmp/{docker_label}_make.log","r",encoding='iso-8859-1')
            compile_result = f.read()
            f.close()
            if "Sanitizer:" in compile_result:
                print("Sanitizer Alert!")
                invalid_functions.append(function_id)
                if not os.path.exists(f"./data/{self.OSS}/{self.model}/fuzzresults"):
                    os.mkdir(f"./data/{self.OSS}/{self.model}/fuzzresults")
                    if not os.path.exists(f"./data/{self.OSS}/{self.model}/fuzzresults/compilefails"):
                        os.mkdir(f"./data/{self.OSS}/{self.model}/fuzzresults/compilefails")
                f = open(f"./data/{self.OSS}/{self.model}/fuzzresults/compilefails/datagen_{function_id_index}.log", 'w', encoding="iso-8859-1")
                f.write(str(patch_function_ids)+"\n"+compile_result)
                f.close()
            elif (self.OSS=="php-src" and "Build complete." not in compile_result) or (self.OSS=="sqlite" and "error: " in compile_result):
                continue
            else:
                if not os.path.exists(f"./data/{self.OSS}/{self.model}/patches/"):
                    os.mkdir(f"./data/{self.OSS}/{self.model}/patches/")
                os.system(f"mv ./data/{self.OSS}/{self.OSS}/test.diff ./data/{self.OSS}/{self.model}/patches/{current_iteration}.diff")
                self.dataset_db.insert_record(self.model, one_percent, f"{current_iteration},{str(patch_function_ids)}", f"./data/{self.OSS}/{self.model}/patches/{current_iteration}.diff")
                current_iteration += 1
                if current_iteration > self.test_iteration_num:
                    break


    # this function evaluates the metric II - Functional Test
    def start_test(self, interval=100):

        one_percent = 73 if self.OSS=="sqlite" else 100

        interval = one_percent

        self.dataset_db = DatasetDB(f"./data/{self.OSS}/{self.model}/dataset.db")
        resultdb = TestResultDB(f"./data/{self.OSS}/{self.model}/test.db")

        if not os.path.exists(f"./data/{self.OSS}/{self.model}/testlog"):
            os.mkdir(f"./data/{self.OSS}/{self.model}/testlog")


        for i in tqdm(range(0,self.test_iteration_num)):
            docker_label = f"test_{self.model}_{self.OSS}"

            try:
                os.system(f"docker kill {docker_label}")
            except:
                pass

            try:
                os.system(f"docker rm {docker_label}")
            except:
                pass
            
            if os.path.exists(f"/tmp/{docker_label}_test.log"):
                os.remove(f"/tmp/{docker_label}_test.log")

            if os.path.exists(f"/tmp/{docker_label}_make.log"):
                os.remove(f"/tmp/{docker_label}_make.log")

            iteration_total = 0
            iteration_passed = 0
            iteration_failed = 0
            iteration_borked = 0
            iteration_skiped = 0

            if self.OSS=="php-src":

                # for each iteration, we start a new docker 
                os.system(f"docker run --name {docker_label} -dit 0599jiangyc/flowfusion4llm:latest bash")

                record = self.dataset_db.fetch_record_by_model_interval_and_id(self.model, interval, i+1)
                func_id, func_model, func_interval, func_label, diffpath = record[0], record[1], record[2], record[3], record[4]
            
                os.system(f"docker cp {diffpath} {docker_label}:/home/phpfuzz/WorkSpace/flowfusion/php-src/")
                os.system(f"docker exec -it {docker_label} bash -c 'cd /home/phpfuzz/WorkSpace/flowfusion/php-src/ && git apply ./{i+1}.diff && timeout 600 make -j16 > ./make.log 2>&1 && git restore *.phpt && timeout 150 make test TEST_PHP_ARGS=\"-j32 --set-timeout 5\" > ./test.log 2>&1'")
                os.system(f"docker cp {docker_label}:/home/phpfuzz/WorkSpace/flowfusion/php-src/make.log /tmp/{docker_label}_make.log")
                os.system(f"docker cp {docker_label}:/home/phpfuzz/WorkSpace/flowfusion/php-src/test.log /tmp/{docker_label}_test.log")

                if os.path.exists(f"/tmp/{docker_label}_test.log"):
                    f = open(f"/tmp/{docker_label}_test.log", 'r' , encoding="iso-8859-1")
                    test_results = f.read()
                    f.close()
                elif os.path.exists(f"/tmp/{docker_label}_make.log"):
                    f = open(f"/tmp/{docker_label}_make.log", 'r' , encoding="iso-8859-1")
                    test_results = f.read()
                    f.close()
                else:
                    test_results = "patching error"

                result_lines = test_results.splitlines()
                for each in result_lines:
                    each = str(each)
                    if ".phpt]" in each:
                        iteration_total += 1
                        # add 'm' due to the color print
                        if "mPASS" in each:
                            iteration_passed += 1
                        elif "mFAIL" in each:                            
                            iteration_failed += 1
                        elif "mSKIP" in each:
                            iteration_skiped += 1
                        else:
                            iteration_borked += 1

            elif self.OSS=="sqlite":
                os.system(f"docker run --name {docker_label} -dit 0599jiangyc/sqlite4llm:latest bash")
                record = self.dataset_db.fetch_record_by_model_interval_and_id(self.model, interval, i+1)
                func_id, func_model, func_interval, func_label, diffpath = record[0], record[1], record[2], record[3], record[4]
            
                os.system(f"docker cp {diffpath} {docker_label}:/home/test/sqlite/")
                os.system(f"docker exec -it {docker_label} bash -c 'su test -c \"cd /home/test/sqlite/ && git apply ./{i+1}.diff && cd build && timeout 600 make -j16 > ./make.log 2>&1 && timeout 150 ./testfixture ../test/testrunner.tcl --jobs 32\"'")
                os.system(f"docker cp {docker_label}:/home/test/sqlite/build/make.log /tmp/{docker_label}_make.log")
                
                os.system(f'docker exec -it {docker_label} bash -c "su test -c \'cd /home/test/sqlite/build && cat ./testrunner.log | grep \\"### test/\\" > ./test.log\'"')

                os.system(f"docker cp {docker_label}:/home/test/sqlite/build/testrunner.log /tmp/{docker_label}_test.log")

                os.system(f"docker cp {docker_label}:/home/test/sqlite/build/test.log /tmp/{docker_label}_testcheck.log")

                if os.path.exists(f"/tmp/{docker_label}_testcheck.log"):
                    f = open(f"/tmp/{docker_label}_testcheck.log", 'r' , encoding="iso-8859-1")
                    test_results = f.read()
                    f.close()
                elif os.path.exists(f"/tmp/{docker_label}_make.log"):
                    f = open(f"/tmp/{docker_label}_make.log", 'r' , encoding="iso-8859-1")
                    test_results = f.read()
                    f.close()
                else:
                    test_results = "patching error"

                result_lines = test_results.splitlines()
                for each in result_lines:
                    iteration_total += 1
                    if "(done)" in each:
                        iteration_passed += 1
                    elif "(failed)" in each:
                        iteration_failed += 1
                    else:
                        continue
            else:
                print("error")
                exit(0)

            print(iteration_failed, iteration_total)

            if os.path.exists(f"/tmp/{docker_label}_test.log"):
                os.system(f"cp /tmp/{docker_label}_test.log ./data/{self.OSS}/{self.model}/testlog/{i+1}.log")
            elif os.path.exists(f"/tmp/{docker_label}_make.log"):
                os.system(f"cp /tmp/{docker_label}_make.log ./data/{self.OSS}/{self.model}/testlog/{i+1}.log")
            else:
                f = open(f"./data/{self.OSS}/{self.model}/testlog/{i+1}.log", "w", encoding="iso-8859-1")
                f.write("patch error.. this should not happen..")
                f.close()

            resultdb.insert_record(
                iteration = i+1,
                total = iteration_total,
                pass_count = iteration_passed,
                fail_count = iteration_failed,
                skip_count = iteration_skiped,
                bork_count = iteration_borked,
                testlog = f"./data/{self.OSS}/{self.model}/testlog/{i+1}.log"
            )

    # this function is the extended evaluation for Metric III -- Memory Safety
    def fuzzloop(self, interval=100):

        # number of test cases to be executed for each iterations
        fuzzsize = 100000

        iterations = 1000

        if not os.path.exists(f"./data/{self.OSS}/{self.model}/fuzzresults/"):
            os.mkdir(f"./data/{self.OSS}/{self.model}/fuzzresults/")

        self.dataset_db = DatasetDB(f"./data/{self.OSS}/{self.model}/dataset.db")

        # we need this because we only want to parse the valid test
        testdb = TestResultDB(f"./data/{self.OSS}/{self.model}/test.db")

        resultdb = FuzzResultDB(f"./data/{self.OSS}/{self.model}/fuzz.db")

        # the test loop

        for i in tqdm(range(0,iterations)):
            
            testid, iteration, total, pass_count, fail_count, skip_count, bork_count, logpath = testdb.fetch_record_by_id(i+1)
            
            if total==0:
                # we skip iterations if failed in tests
                continue

            docker_label = f"fuzz_{self.model}_{self.OSS}"

            try:
                os.system(f"docker kill {docker_label}")
            except:
                pass

            try:
                os.system(f"docker rm {docker_label}")
            except:
                pass
            
            if os.path.exists(f"/tmp/{docker_label}_fuzz.log"):
                os.remove(f"/tmp/{docker_label}_fuzz.log")

            if os.path.exists(f"/tmp/{docker_label}_make.log"):
                os.remove(f"/tmp/{docker_label}_make.log")

            # for each iteration, we start a new docker 
            os.system(f"docker run --name {docker_label} -dit 0599jiangyc/flowfusion4llm4fuzz:latest bash")

            record = self.dataset_db.fetch_record_by_model_interval_and_id(self.model, interval, i+1)
            func_id, func_model, func_interval, func_label, diffpath = record[0], record[1], record[2], record[3], record[4]
        
            os.system(f"docker cp {diffpath} {docker_label}:/home/phpfuzz/WorkSpace/flowfusion/php-src/")
            
            os.system(f"docker exec -it {docker_label} bash -c 'cd /home/phpfuzz/WorkSpace/flowfusion/php-src/ && git apply ./{i+1}.diff && timeout 600 make -j16 > ./make.log 2>&1'")
            
            os.system(f"docker exec -it {docker_label} bash -c 'cd /home/phpfuzz/WorkSpace/flowfusion/ && sed -i \"s/self\.stopping_test_num = -1/self.stopping_test_num = {fuzzsize}/g\" ./main.py'")
            
            os.system(f"docker exec -it {docker_label} bash -c 'cd /home/phpfuzz/WorkSpace/flowfusion/ && timeout 1800 python3 main.py'")
            
            os.system(f"docker exec -it {docker_label} bash -c 'cd /home/phpfuzz/WorkSpace/flowfusion/ && mv ./bugs ./{i+1}_bugs && zip -r bugs.zip ./{i+1}_bugs'")
            
            os.system(f"docker cp {docker_label}:/home/phpfuzz/WorkSpace/flowfusion/php-src/make.log /tmp/{docker_label}_make.log")
            os.system(f"docker cp {docker_label}:/home/phpfuzz/WorkSpace/flowfusion/bugs.zip /tmp/{docker_label}_bugs.zip")

            if not os.path.exists(f"/tmp/{docker_label}_bugs.zip"):
                print("why?")
                input()
            else:
                os.system(f"cp /tmp/{docker_label}_bugs.zip ./data/{self.OSS}/{self.model}/fuzzresults/{i+1}.zip")

def main():
    parser = argparse.ArgumentParser(description="Run OSSBench with various actions.")
    parser.add_argument("--model",
                        default="llama3-8b-seed0",
                        help="Specify the model (e.g., 'llama3-8b-seed0')")
    parser.add_argument("--OSS",
                        default="php-src",
                        help="Specify the OSS project (e.g., 'php-src')")

    # Flags for which action to run:
    parser.add_argument("--linear-execution",
                        action="store_true",
                        help="Call bench.linear_execution()")
    parser.add_argument("--dataset-generation",
                        action="store_true",
                        help="Call bench.dataset_generation()")
    parser.add_argument("--test",
                        action="store_true",
                        help="Call bench.start_test()")
    parser.add_argument("--fuzz",
                        action="store_true",
                        help="Call bench.fuzzloop()")

    args = parser.parse_args()

    bench = OSSBench(model=args.model, OSS=args.OSS)

    # Decide which action to run based on the flags:
    if args.linear_execution:
        bench.linear_execution()
    elif args.dataset_generation:
        bench.dataset_generation()
    elif args.test:
        bench.start_test()
    elif args.fuzz:
        bench.fuzzloop()
    else:
        print("nothing to do")
        


if __name__ == "__main__":
    main()
