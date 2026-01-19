import asyncio
import aiohttp
import time
import random
import argparse
import sys

async def simulate_lamp(session, base_url, arduino_id, start_delay, lamp_idx):
    await asyncio.sleep(start_delay)
    headers = {'User-Agent': 'ESP32', 'Accept': 'application/json'}
    url = f"{base_url.rstrip('/')}/api/arduino/v2/{arduino_id}/data"
    
    while True:
        try:
            start_time = time.time()
            async with session.get(url, headers=headers, timeout=60) as response:
                status = response.status
                await response.text()
                duration = time.time() - start_time
                log_msg = f"[{time.strftime('%H:%M:%S')}] Lamp_{lamp_idx}: {status} in {duration:.2f}s\n"
                with open("stable_test_log.txt", "a") as f:
                    f.write(log_msg)
        except Exception as e:
            error_msg = f"[{time.strftime('%H:%M:%S')}] Lamp_{lamp_idx}: Error {type(e).__name__}\n"
            with open("stable_test_log.txt", "a") as f:
                f.write(error_msg)
        
        # 13-minute poll interval
        await asyncio.sleep(780 + random.uniform(-5, 5))

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    args = parser.parse_args()
    
    num_lamps = 1500
    print(f"⚖️  Testing STABILITY for {num_lamps} lamps...")
    print(f"📊 Target RPS: {num_lamps/780:.2f} (should remain stable)")
    print(f"📝 Logging to stable_test_log.txt")
    
    connector = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(connector=connector) as session:
        stagger_step = 780 / num_lamps 
        tasks = []
        for i in range(num_lamps):
            task = asyncio.create_task(simulate_lamp(session, args.url, [12, 8, 100, 5, 3, 6, 7, 4][i % 8], i * stagger_step, i))
            tasks.append(task)
            if (i+1) % 100 == 0:
                print(f"   Scheduled {i+1} lamps...")
        
        # Monitor for 20 minutes
        await asyncio.sleep(1200)

if __name__ == "__main__":
    with open("stable_test_log.txt", "w") as f:
        f.write(f"Stability Test Started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    asyncio.run(main())
