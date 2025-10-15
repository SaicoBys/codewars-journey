#!/usr/bin/env python3
"""
Codewars Auto-Sync 2.0
Optimized script for importing solutions from Codewars API
Designed for reliability and simplicity
"""

import requests
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

class CodewarsSync:
    def __init__(self, username: str = "SaicoBys"):
        self.username = username
        self.base_url = "https://www.codewars.com/api/v1"
        self.session = requests.Session()

        # Rate limiting - be respectful to Codewars API
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds between requests

    def _rate_limit(self):
        """Enforce rate limiting between API requests"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time

        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def get_user_profile(self) -> Dict:
        """Get user profile information"""
        self._rate_limit()

        try:
            response = self.session.get(f"{self.base_url}/users/{self.username}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ Error fetching user profile: {e}")
            return {}

    def get_completed_challenges(self, limit: int = 50) -> List[Dict]:
        """Get completed challenges for the user"""
        all_challenges = []
        page = 0

        print(f"🔍 Fetching completed challenges for {self.username}...")

        while len(all_challenges) < limit:
            self._rate_limit()

            try:
                url = f"{self.base_url}/users/{self.username}/code-challenges/completed"
                params = {'page': page}

                response = self.session.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                challenges = data.get('data', [])
                if not challenges:
                    break

                # Filter for Python challenges only
                python_challenges = [c for c in challenges if 'python' in c.get('completedLanguages', [])]
                all_challenges.extend(python_challenges)

                print(f"📄 Page {page + 1}: Found {len(python_challenges)} Python challenges")

                # Check if we have enough or if there are more pages
                total_pages = data.get('totalPages', 1)
                if page >= total_pages - 1:
                    break

                page += 1

            except requests.RequestException as e:
                print(f"❌ Error fetching page {page}: {e}")
                break

        # Limit to requested amount
        all_challenges = all_challenges[:limit]
        print(f"✅ Total Python challenges found: {len(all_challenges)}")
        return all_challenges

    def rank_to_folder(self, rank: int) -> str:
        """Convert Codewars rank to folder name"""
        rank_map = {
            -8: "8kyu", -7: "7kyu", -6: "6kyu", -5: "5kyu",
            -4: "4kyu", -3: "3kyu", -2: "2kyu", -1: "1kyu"
        }
        return rank_map.get(rank, "other")

    def sanitize_filename(self, name: str) -> str:
        """Convert kata name to valid filename"""
        import re
        # Remove special characters and replace spaces with underscores
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'\s+', '_', name)
        return name.lower()

    def get_challenge_details(self, challenge_id: str) -> Dict:
        """Get detailed information about a specific challenge"""
        self._rate_limit()

        try:
            response = self.session.get(f"{self.base_url}/code-challenges/{challenge_id}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ Error fetching challenge {challenge_id}: {e}")
            return {}

    def create_kata_file(self, challenge: Dict, challenge_details: Dict) -> bool:
        """Create a minimal Python file for the kata"""
        try:
            # Get challenge info
            name = challenge['name']
            kata_id = challenge['id']
            completed_at = challenge['completedAt'][:10]  # Just the date

            # Get difficulty from details
            rank = challenge_details.get('rank', {}).get('id', -8)
            folder = self.rank_to_folder(rank)

            # Create folder if it doesn't exist
            os.makedirs(folder, exist_ok=True)

            # Generate filename
            filename = self.sanitize_filename(name)
            filepath = f"{folder}/{filename}.py"

            # Skip if file already exists
            if os.path.exists(filepath):
                return False

            # Create minimal file content
            content = f'''"""
🎯 {name} - {folder}
🔗 https://www.codewars.com/kata/{kata_id}
📅 Completed: {completed_at}
"""

# TODO: Add your solution here
# This kata was completed on Codewars on {completed_at}

def solution():
    pass


if __name__ == "__main__":
    print("Solution for: {name}")
    # Add test cases here
'''

            # Write file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"📝 Created: {filepath}")
            return True

        except Exception as e:
            print(f"❌ Error creating file for {challenge['name']}: {e}")
            return False

    def update_readme_stats(self) -> bool:
        """Update README with current statistics"""
        try:
            # Count katas in each folder
            difficulties = ['8kyu', '7kyu', '6kyu', '5kyu', '4kyu', '3kyu', '2kyu', '1kyu']
            stats = {}
            total_solved = 0

            for diff in difficulties:
                if os.path.exists(diff):
                    count = len([f for f in os.listdir(diff) if f.endswith('.py')])
                    stats[diff] = count
                    total_solved += count
                else:
                    stats[diff] = 0

            # Calculate progress bars
            progress_bars = {}
            for diff, count in stats.items():
                if total_solved > 0:
                    percentage = (count / total_solved) * 100
                    filled = int(percentage // 10)
                    bar = "█" * filled + "░" * (10 - filled)
                    progress_bars[diff] = f"{bar} {percentage:.1f}%"
                else:
                    progress_bars[diff] = "░░░░░░░░░░ 0%"

            # Read current README
            with open('README.md', 'r', encoding='utf-8') as f:
                readme_content = f.read()

            # Update total katas
            readme_content = readme_content.replace(
                f'- **Total Katas Solved**: 0 *(auto-updates)*',
                f'- **Total Katas Solved**: {total_solved} *(auto-updates)*'
            )

            # Update difficulty breakdown table
            table_lines = []
            for diff in difficulties:
                count = stats[diff]
                progress = progress_bars[diff]
                table_lines.append(f"| {diff} | {count} | {progress} |")

            new_table = '\n'.join(table_lines)

            # Replace the table in README
            import re
            # Find the table section between the header and the next section
            pattern = r'(### 🎯 Difficulty Breakdown\n\n)\| Rank \| Solved \| Progress \|.*?(?=\n---|\n## |\n\n## |\Z)'
            replacement = f'\\1| Rank | Solved | Progress |\n|------|--------|----------|\n{new_table}\n'
            readme_content = re.sub(pattern, replacement, readme_content, flags=re.DOTALL)

            # Update last updated timestamp
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
            readme_content = readme_content.replace(
                '- **Last Updated**: *Auto-sync daily*',
                f'- **Last Updated**: {current_time}'
            )

            # Write updated README
            with open('README.md', 'w', encoding='utf-8') as f:
                f.write(readme_content)

            print(f"📊 README updated with {total_solved} total katas")
            return True

        except Exception as e:
            print(f"❌ Error updating README: {e}")
            return False

    def sync_new_challenges(self, limit: int = 20) -> int:
        """Sync new challenges and return count of new files created"""
        print("🚀 Starting Codewars sync...")

        # Get user profile for stats
        profile = self.get_user_profile()
        if profile:
            total_completed = profile.get('codeChallenges', {}).get('totalCompleted', 0)
            current_rank = profile.get('ranks', {}).get('overall', {}).get('name', 'Unknown')
            print(f"👤 User: {self.username}")
            print(f"🏆 Current rank: {current_rank}")
            print(f"🎯 Total completed: {total_completed}")

        # Get completed challenges
        challenges = self.get_completed_challenges(limit)
        if not challenges:
            print("❌ No challenges found")
            return 0

        # Process challenges
        new_files = 0
        for i, challenge in enumerate(challenges):
            print(f"🔄 Processing {i+1}/{len(challenges)}: {challenge['name']}")

            # Get challenge details
            details = self.get_challenge_details(challenge['id'])
            if details:
                if self.create_kata_file(challenge, details):
                    new_files += 1

        # Update README stats
        self.update_readme_stats()

        print(f"✅ Sync complete! Created {new_files} new files")
        return new_files


def main():
    """Main function to run the sync"""
    syncer = CodewarsSync("SaicoBys")
    new_files = syncer.sync_new_challenges(limit=10)  # Limit to 10 for initial sync

    if new_files > 0:
        print(f"\n🎉 {new_files} new kata files created!")
    else:
        print("\n✅ No new files to create - you're up to date!")


if __name__ == "__main__":
    main()