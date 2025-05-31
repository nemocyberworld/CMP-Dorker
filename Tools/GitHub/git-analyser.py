import os
import requests
import subprocess
import datetime
from git import Repo

def main():
    org = input("🔎 Enter the target GitHub organization or user name: ").strip()
    if not org:
        print("❌ You must enter a valid GitHub org/user name!")
        return

    github_api = f"https://api.github.com/orgs/{org}/repos?per_page=100"
    user_api = f"https://api.github.com/users/{org}/repos?per_page=100"
    
    workspace = f"{org}_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(workspace, exist_ok=True)

    def fetch_repos():
        print(f"🔍 Fetching public repositories for {org}...")
        repos = []
        page = 1

        api_url = github_api
        while True:
            res = requests.get(f"{api_url}&page={page}")
            if res.status_code == 404:
                if api_url == github_api:
                    api_url = user_api
                    page = 1
                    continue
                else:
                    print("❌ GitHub user/org not found.")
                    return []
            elif res.status_code != 200:
                print("❌ GitHub API error:", res.status_code)
                return []
            data = res.json()
            if not data:
                break
            repos.extend(data)
            page += 1
        return [repo["clone_url"] for repo in repos]

    def clone_repo(url):
        repo_name = url.split("/")[-1].replace(".git", "")
        target_path = os.path.join(workspace, repo_name)
        if os.path.exists(target_path):
            print(f"✅ Repo {repo_name} already cloned. Skipping.")
            return target_path
        try:
            print(f"⬇️ Cloning {repo_name}...")
            Repo.clone_from(url, target_path)
        except Exception as e:
            print(f"⚠️ Failed to clone {url}: {e}")
        return target_path

    def run_command(cmd, cwd=None):
        try:
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {' '.join(cmd)}")
            print(e.stderr)
            return None

    def run_bandit(repo_path):
        print(f"🔐 Running Bandit on {repo_path}...")
        result_path = os.path.join(repo_path, "bandit_report.txt")
        cmd = ["bandit", "-r", repo_path, "-f", "txt", "-o", result_path]

        # Run without check=True to avoid error on findings
        result = subprocess.run(cmd, capture_output=True, text=True)
        if os.path.exists(result_path):
            print(f"✅ Bandit report saved to {result_path}")
        else:
            print(f"❌ Bandit failed to create report in {repo_path}")
            print("Bandit stderr:", result.stderr)

    def run_gitleaks(repo_path):
        print(f"🔑 Running Gitleaks on {repo_path}...")
        result_path = os.path.join(repo_path, "gitleaks_report.json")
        cmd = ["gitleaks", "detect", "-s", repo_path, "--report-format", "json", "--report-path", result_path]
        if run_command(cmd) is None:
            print(f"⚠️ Gitleaks scan failed for {repo_path}")
        else:
            print(f"✅ Gitleaks report saved to {result_path}")

    def run_trufflehog(repo_path):
        print(f"🕵️ Running truffleHog on {repo_path}...")
        result_path = os.path.join(repo_path, "trufflehog_report.json")
        with open(result_path, "w") as outfile:
            try:
                subprocess.run(
                    ["trufflehog", "filesystem", "--directory", repo_path, "--json"],
                    stdout=outfile,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
                print(f"✅ Trufflehog report saved to {result_path}")
            except subprocess.CalledProcessError:
                print(f"⚠️ Trufflehog scan failed for {repo_path}")

    repos = fetch_repos()
    if not repos:
        print("❌ No repositories found.")
        return

    for repo_url in repos:
        repo_path = clone_repo(repo_url)
        run_bandit(repo_path)
        run_gitleaks(repo_path)
        run_trufflehog(repo_path)

    print(f"\n✅ Analysis complete. Reports saved in: {workspace}")

if __name__ == "__main__":
    main()
