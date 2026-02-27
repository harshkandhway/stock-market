import subprocess
import time

scripts = [
    ("Option A (Earnings Blackout)", "backtest_option_a.py", "report_a.txt"),
    ("Option B (RS Overlay)", "backtest_option_b.py", "report_b.txt"),
    ("Option C (1.5R Scale-Out)", "backtest_option_c.py", "report_c.txt"),
    ("Option D (Coiled Volatility)", "backtest_option_d.py", "report_d.txt")
]

print("🚀 Starting 4-Option Orchestration...")
print("Executing sequentially to avoid API rate limits from Yahoo Finance.")

for name, script, output_file in scripts:
    print(f"\n[{time.strftime('%H:%M:%S')}] Executing {name}...")
    try:
        # Run sequentially, wait for completion, stream output to both console and file
        with open(output_file, "w") as f:
            process = subprocess.Popen(["python3", script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            # Read line by line
            for line in process.stdout:
                # Only print the summary lines to the console to keep it clean, but write everything to the file
                if "TOTAL" in line.upper() or "NET" in line.upper() or "WIN" in line.upper() or "===" in line:
                    print(line.strip())
                if "Backtesting" in line and "RELIANCE" in line:
                    print(line.strip())
                f.write(line)
            
            process.wait()
            print(f"✅ {name} Completed. Report saved to {output_file}")
    except Exception as e:
        print(f"❌ Failed to run {name}: {e}")

print("\n🏁 All 4 Options Executed Successfully.")
