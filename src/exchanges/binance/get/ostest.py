# -*- coding: utf-8 -*-
"""
Created on Sun Jul 14 21:23:45 2024

@author: dalil
"""
# from src.marketmaking.sharedstate import MMSharedState
import os

# current_script_path = os.path.abspath(__file__)

# print(f"current script path : {current_script_path}")

# dirname = os.path.dirname(current_script_path)

# print(f"dirname is : {dirname}")

# repo_root = os.path.dirname(os.path.dirname(current_script_path))

# current_folder = os.path.dirname(os.path.abspath(__file__))
# while current_folder.split('\\')[-1] != "src":
#     current_folder = current_folder = os.path.dirname(current_folder)
        
# print(os.path.join(current_folder, 'marketmaking', 'parameters.yaml'))


# ss = MMSharedState(False)

import asyncio
import time

async def just_waiting(delay):
    await asyncio.sleep(delay)
    print(f"{delay} seconds have passed")

async def say_after(delay, what):
    await just_waiting(delay)
    print(what)
    return f"Returned value: {what}"

def other_blocking_function():
    time.sleep(3)
    print("Other blocking function executed")

async def main():
    print(f"started at {time.strftime('%X')}")

    task1 = say_after(5, 'hello')  # No need to await asyncio.create_task
    task2 = say_after(2, 'world')  # No need to await asyncio.create_task
    
    print(f"time before the first await: {time.strftime('%X')}")
    result1 = await asyncio.create_task(task1)
    print(f"time after the first await and before the second: {time.strftime('%X')}")
    result2 = await asyncio.create_task(task2)
    print(f"time after the second await: {time.strftime('%X')}")

    print("Hello World!")
    other_blocking_function()

    # After 3 seconds, both tasks should be completed
    await asyncio.sleep(1)  # Adding this line to simulate a delay

    print(result1)
    print(result2)

    print(f"finished at {time.strftime('%X')}")
    await asyncio.sleep(30)  # Adding this line to simulate a delay

asyncio.run(main())