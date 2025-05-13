#!/usr/bin/env python3

import os
import json
import argparse
import difflib
from tqdm import tqdm
from docker import OSSBenchDocker
from sqlite3db import FunctionDB, DatasetDB, TestResultDB, FuzzResultDB

verbose = 0

# note: now we score in pass@1
# TODO: support pass@k


# make sure error less than 20
# ad-hoc fixing prompt response errors, this will have trivial impact on results

def calculating_error_count(model, oss):

    print("\t0. error count: " + model)

    if not os.path.exists(f"./data/{oss}/{model}/function.db"):
        print("file does not exist")
    db = FunctionDB(f"./data/{oss}/{model}/function.db")
    total_number = 10534 if oss=="php-src" else 7321
    error_count = 0 
    for i in range(0, total_number):
        i, idx, filepath, token_number, old, new = db.fetch_function_by_id(i+1)
        # Count different lines between old and new
        
        if "Error:" in new:
            error_count += 1
    print("\t\terror count: ", error_count)
    return error_count

def calculating_similarity_score(model, oss):

    print("\t0. calculating similarity score: " + model)

    filename = '/var/www/html/oss-bench/results.json'

    # Open the file in read mode and load the JSON content into a dictionary
    with open(filename, 'r') as json_file:
        data = json.load(json_file)

    if not os.path.exists(f"./data/{oss}/{model}/function.db"):
        print("file does not exist")
    db = FunctionDB(f"./data/{oss}/{model}/function.db")
    total_number = 10534 if oss=="php-src" else 7321
    total_diff_count = 0
    for i in range(0, total_number):
        i, idx, filepath, token_number, old, new = db.fetch_function_by_id(i+1)
        # Count different lines between old and new
        
        # Split strings into lines for line-by-line comparison
        old_lines = old.strip('\n').splitlines()
        new_lines = new.strip('\n').splitlines()
        
        # Use difflib to get line differences
        
        diff = difflib.ndiff(old_lines, new_lines)

        # Count lines that are different (start with '+ ', '- ')
        diff_count = sum(1 for line in diff if line.startswith(('+ ', '- ')))
        
        total_diff_count += diff_count
        
    diff_score = round(total_diff_count/total_number, 2)
    print(f"\t\t{model} in {oss}: the average diff count per function is", diff_score)

    mark = 0
    oss_index = 0 if oss=="php-src" else 1

    for x in data['benchmarks'][oss_index]["data"]:
        if x["model_name"]==model.split('-seed')[0]:
            x["dissimilarity"] = diff_score
            mark = 1
    
    if mark==0:
        data['benchmarks'][oss_index]["data"].append({
            "model_name": model.split('-seed')[0],
            "dissimilarity": diff_score,
            "task1:compilation_score": 0,
            "task2:test_score": 0,
            "task3:sanitizer_score": 0,
            "size": 30
        })
    
    with open("/var/www/html/oss-bench/results.json", 'w') as json_file:
        json.dump(data, json_file, indent=4)

def marking_linear_compilation(model, oss):

    print("\t1. marking linear compilation: " + model)

    filename = '/var/www/html/oss-bench/results.json'

    # Open the file in read mode and load the JSON content into a dictionary
    with open(filename, 'r') as json_file:
        resultdata = json.load(json_file)    

    if not os.path.exists(f"./data/{oss}/{model}/function.db"):
        print("\t\t!!file does not exist")
    db = FunctionDB(f"./data/{oss}/{model}/function.db")

    if not os.path.exists(f"./data/{oss}/{model}"):
        print("\t\t!!file does not exist")
    if not os.path.exists(f"./data/{oss}/{model}/linear_compile_fail_logs"):
        print("\t\t!!file does not exist")
    if not os.path.exists(f"./data/{oss}/{model}/fuzzresults/compilefails"):
        print("\t\t!!file does not exist")

    filename = '/var/www/html/oss-bench/compile.json'

    # Open the file in read mode and load the JSON content into a dictionary
    with open(filename, 'r') as json_file:
        data = json.load(json_file)

    total_number = 10534 if oss=="php-src" else 7321
    fails = []
    sanitizer_alerts = []
    json_array = []
    faillogs = os.listdir(f"./data/{oss}/{model}/linear_compile_fail_logs")
    for each in faillogs:
        fid = int(each.split('.')[0])
        i, idx, filepath, token_number, old, new = db.fetch_function_by_id(fid)
        fails.append(fid)
        f = open(f"./data/{oss}/{model}/linear_compile_fail_logs/{each}","r",encoding="iso-8859-1")
        info = f.read()
        f.close()
        infolines = info.splitlines()
        if len(infolines)>20:
            infolines = ["..."]+infolines[-20:]
        for i in range(len(infolines)):
            if len(infolines[i])>100:
                infolines[i] = infolines[i][:100]+".."
        json_array.append({
            "id": int(fid),
            "function_name": idx,
            "compile_alerts": "***compilation failed***\n<br>"+"\n<br>".join(infolines) if verbose==1 else "***compilation failed***"
        })
    fuzzlogs = os.listdir(f"./data/{oss}/{model}/fuzzresults/compilefails")
    for each in fuzzlogs:
        if "datagen" in each:
            continue
        fid = int(each.split('.')[0])
        i, idx, filepath, token_number, old, new = db.fetch_function_by_id(fid)
        sanitizer_alerts.append(int(each.split('.')[0]))
        f = open(f"./data/{oss}/{model}/fuzzresults/compilefails/{each}","r",encoding="iso-8859-1")
        info = f.read()
        f.close()
        infolines = info.splitlines()
        if len(infolines)>20:
            infolines = ["..."]+infolines[-20:]
        for i in range(len(infolines)):
            if len(infolines[i])>100:
                infolines[i] = infolines[i][:100]+".."
        json_array.append({
            "id": fid,
            "function_name": idx,
            "compile_alerts": "***sanitizer alerts in compilation***\n<br>"+"\n<br>".join(infolines) if verbose==1 else "***sanitizer alerts in compilation***"
        })

    passnum = total_number - len(fails) - len(sanitizer_alerts)
    compilation_score = round((passnum/total_number)*100, 2)
    print(f"\t\tthe compilation score is {compilation_score}")

    oss_string = 'php' if oss=="php-src" else 'sqlite'

    data[oss_string][model.split('-seed')[0]] = json_array
    
    with open("/var/www/html/oss-bench/compile.json", 'w') as json_file:
        json.dump(data, json_file, indent=4)

    oss_index = 0 if oss=="php-src" else 1

    for x in resultdata['benchmarks'][oss_index]["data"]:
        if x["model_name"]==model.split('-seed')[0]:
            x["task1:compilation_score"] = compilation_score

    with open("/var/www/html/oss-bench/results.json", 'w') as json_file:
        json.dump(resultdata, json_file, indent=4)

def marking_tests(model, oss):

    print("\t2. marking tests: " + model)

    if not os.path.exists(f"./data/{oss}/{model}/function.db"):
        print("\t\tfunction.db does not exist")
        exit()
    
    if not os.path.exists(f"./data/{oss}/{model}/test.db"):
        print("\t\ttest.db does not exist")
        exit()

    testdb = TestResultDB(f"./data/{oss}/{model}/test.db")

    filename = '/var/www/html/oss-bench/results.json'

    # Open the file in read mode and load the JSON content into a dictionary
    with open(filename, 'r') as json_file:
        resultdata = json.load(json_file)

    filename = '/var/www/html/oss-bench/test.json'
    # Open the file in read mode and load the JSON content into a dictionary
    with open(filename, 'r') as json_file:
        data = json.load(json_file)

    valid_count = 0
    total_pass_count = 0
    total_total = 0

    testjsondata = []

    for i in range(0,1000):
        testid = i+1
        try:
            testid, iteration, total, pass_count, fail_count, skip_count, bork_count, logpath = testdb.fetch_record_by_id(i+1)
        except:
            break
        if total-skip_count==0:
            passrate = -1
        else:
            valid_count += 1
            total_pass_count += pass_count
            total_total += total-skip_count
            passrate = pass_count/(total-skip_count)

        testjsondata.append({
            'testid': testid,
            'passrate': passrate
        })

        # data['php'][model.split('-seed')[0]][i] = {
        #     'testid': testid,
        #     'passrate': passrate
        # }

    if total_total==0:
        print("0 lah")
        return

    oss_string = 'php' if oss=="php-src" else 'sqlite'

    data[oss_string][model.split('-seed')[0]] = testjsondata

    average_score = total_pass_count/total_total*100

    final_score = round(average_score*valid_count/1000, 2)

    print(f"\t\tthe average score is {average_score}")
    print(f"\t\tthe test score is {final_score}")

    with open("/var/www/html/oss-bench/test.json", 'w') as json_file:
        json.dump(data, json_file, indent=4)

    oss_index = 0 if oss=="php-src" else 1

    for x in resultdata['benchmarks'][oss_index]["data"]:
        if x["model_name"]==model.split('-seed')[0]:
            x["task2:test_score"] = final_score

    with open("/var/www/html/oss-bench/results.json", 'w') as json_file:
        json.dump(resultdata, json_file, indent=4)

def marking_memsafe(model, oss):

    print("\t3. marking memsafe: " + model)

    filename = '/var/www/html/oss-bench/results.json'

    # Open the file in read mode and load the JSON content into a dictionary
    with open(filename, 'r') as json_file:
        resultdata = json.load(json_file)

    filename = '/var/www/html/oss-bench/fuzz.json'
    # Open the file in read mode and load the JSON content into a dictionary
    with open(filename, 'r') as json_file:
        data = json.load(json_file)

    sanitizer_alerts = set()
    os.system(f"cd ./data/{oss}/{model}/ && find ./ -name '*.log' -type f | xargs egrep -a 'SUMMARY:' | cut -d: -f2- | sort -u > ./summary.txt")        
    
    f = open(f"./data/{oss}/{model}/summary.txt","r")
    info = f.read()
    f.close()
    
    infolines = info.splitlines()
    for eachinfo in infolines:
        eachinfo = eachinfo.replace('/home/phpfuzz/WorkSpace/flowfusion/php-src/', '')
        eachinfo = eachinfo.strip(' ')
        if "TEST" in eachinfo:
            continue
        if "/dev/zero" in eachinfo:
            sanitizer_alerts.add(eachinfo.split('/dev/zero')[0]+'/dev/zero)')
        else:
            sanitizer_alerts.add(eachinfo)
    
    oss_string = 'php' if oss=="php-src" else 'sqlite'

    data[oss_string][model.split('-seed')[0]] = list(sanitizer_alerts)

    with open("/var/www/html/oss-bench/fuzz.json", 'w') as json_file:
        json.dump(data, json_file, indent=4)
    
    final_score = round(100 - len(list(sanitizer_alerts))*0.88, 2)
    if final_score< 0:
        final_score = 0.01

    oss_index = 0 if oss=="php-src" else 1

    for x in resultdata['benchmarks'][oss_index]["data"]:
        if x["model_name"]==model.split('-seed')[0]:
            x["task3:sanitizer_score"] = final_score

    with open("/var/www/html/oss-bench/results.json", 'w') as json_file:
        json.dump(resultdata, json_file, indent=4)
    

def main():

    oss = "php-src"
    oss = "sqlite"

    models = os.listdir(f"./data/{oss}/")
    for each in models:
        if ".db" in each or each==oss:
            continue
        # if each!="qwen3-30b-a3b-fp16-seed0":
        #     continue
        print(f"======scoring {each}======")
        try:
            calculating_error_count(each, oss)
            calculating_similarity_score(each, oss)
            marking_linear_compilation(each, oss)
            marking_tests(each, oss)
            marking_memsafe(each, oss)
        except Exception as e:
            print(str(e))
            print(each)

main()
