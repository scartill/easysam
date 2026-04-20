import subprocess
import sys
from pathlib import Path


def test_generation():
    examples_dir = Path('example')
    results = []

    # List all subdirectories in example/
    example_dirs = [d for d in examples_dir.iterdir() if d.is_dir()]

    # Sort for consistent output
    example_dirs.sort()

    print(f'Testing generation for {len(example_dirs)} examples...\n')

    for example_path in example_dirs:
        # Construct the command as requested
        # Using the user's suggested profile/environment names
        cmd = [
            'uv',
            'run',
            'easysam',
            '--aws-profile',
            'easysam-a',
            '--environment',
            'easysamdev',
            '--target-region',
            'us-east-1',
            'generate',
            str(example_path) + '\\',
        ]

        print(f'Testing: {example_path.name}...', end=' ', flush=True)

        try:
            # Run the command and capture output
            process = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if process.returncode == 0:
                print('\033[92mPASS\033[0m')
                results.append((example_path.name, True, ''))
            else:
                # Some examples might be expected to fail (like appwitherrors)
                if 'appwitherrors' in example_path.name:
                    print('\033[93mEXPECTED FAIL\033[0m')
                    results.append((example_path.name, True, '(Expected failure)'))
                else:
                    print('\033[91mFAIL\033[0m')
                    error_msg = process.stderr or process.stdout
                    results.append((example_path.name, False, error_msg))

        except Exception as e:
            print('\033[91mERROR\033[0m')
            results.append((example_path.name, False, str(e)))

    # Report results
    print('\n' + '=' * 50)
    print('Generation Test Results Summary')
    print('=' * 50)

    passed_count = sum(1 for _, success, _ in results if success)
    failed_count = len(results) - passed_count

    for name, success, note in results:
        status = '\033[92m[PASS]\033[0m' if success else '\033[91m[FAIL]\033[0m'
        print(f'{status} {name} {note}')

    print('=' * 50)
    print(f'Total: {len(results)} | Passed: {passed_count} | Failed: {failed_count}')

    if failed_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    test_generation()
