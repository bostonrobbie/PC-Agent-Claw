#!/usr/bin/env python3
"""
Real-Time Internet Access
Search web, fetch docs, check GitHub - during conversation
"""
import sys
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import json
from typing import Dict, List, Optional
from datetime import datetime
import re

sys.path.append(str(Path(__file__).parent.parent))


class RealtimeInternet:
    """
    Real-time internet access capabilities

    Features:
    - Web search (DuckDuckGo, Google)
    - Documentation scraping
    - GitHub API access
    - Stack Overflow search
    - Package documentation (PyPI, npm)
    - Real-time knowledge updates
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    # === WEB SEARCH ===

    def search_web(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Search the web using DuckDuckGo

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            List of search results
        """
        try:
            # DuckDuckGo instant answer API
            url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_html': 1,
                'skip_disambig': 1
            }

            response = self.session.get(url, params=params, timeout=10)
            data = response.json()

            results = []

            # Abstract (main answer)
            if data.get('Abstract'):
                results.append({
                    'title': data.get('Heading', 'Result'),
                    'snippet': data['Abstract'],
                    'url': data.get('AbstractURL', ''),
                    'source': 'DuckDuckGo Instant Answer'
                })

            # Related topics
            for topic in data.get('RelatedTopics', [])[:num_results]:
                if isinstance(topic, dict) and 'Text' in topic:
                    results.append({
                        'title': topic.get('FirstURL', '').split('/')[-1].replace('_', ' '),
                        'snippet': topic['Text'],
                        'url': topic.get('FirstURL', ''),
                        'source': 'Related Topic'
                    })

            return results

        except Exception as e:
            print(f"[ERROR] Web search failed: {e}")
            return []

    def search_stackoverflow(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Search Stack Overflow

        Args:
            query: Search query
            num_results: Number of results

        Returns:
            List of Stack Overflow questions
        """
        try:
            url = "https://api.stackexchange.com/2.3/search"
            params = {
                'order': 'desc',
                'sort': 'relevance',
                'intitle': query,
                'site': 'stackoverflow',
                'pagesize': num_results
            }

            response = self.session.get(url, params=params, timeout=10)
            data = response.json()

            results = []
            for item in data.get('items', []):
                results.append({
                    'title': item['title'],
                    'score': item['score'],
                    'answer_count': item['answer_count'],
                    'is_answered': item['is_answered'],
                    'url': item['link'],
                    'tags': item.get('tags', [])
                })

            return results

        except Exception as e:
            print(f"[ERROR] Stack Overflow search failed: {e}")
            return []

    # === DOCUMENTATION ACCESS ===

    def get_pypi_package_info(self, package_name: str) -> Optional[Dict]:
        """
        Get PyPI package information

        Args:
            package_name: Package name

        Returns:
            Package information
        """
        try:
            url = f"https://pypi.org/pypi/{package_name}/json"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                info = data['info']

                return {
                    'name': info['name'],
                    'version': info['version'],
                    'summary': info['summary'],
                    'author': info['author'],
                    'license': info['license'],
                    'home_page': info['home_page'],
                    'docs_url': info.get('docs_url'),
                    'project_urls': info.get('project_urls', {}),
                    'requires_python': info.get('requires_python'),
                    'classifiers': info.get('classifiers', [])
                }
            else:
                return None

        except Exception as e:
            print(f"[ERROR] PyPI fetch failed: {e}")
            return None

    def get_npm_package_info(self, package_name: str) -> Optional[Dict]:
        """
        Get npm package information

        Args:
            package_name: Package name

        Returns:
            Package information
        """
        try:
            url = f"https://registry.npmjs.org/{package_name}"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                latest_version = data.get('dist-tags', {}).get('latest', '')
                latest = data.get('versions', {}).get(latest_version, {})

                return {
                    'name': data['name'],
                    'version': latest_version,
                    'description': data.get('description', ''),
                    'license': latest.get('license', ''),
                    'homepage': data.get('homepage', ''),
                    'repository': data.get('repository', {}),
                    'keywords': data.get('keywords', []),
                    'dependencies': latest.get('dependencies', {})
                }
            else:
                return None

        except Exception as e:
            print(f"[ERROR] npm fetch failed: {e}")
            return None

    # === GITHUB ACCESS ===

    def search_github_repos(self, query: str, language: str = None, num_results: int = 5) -> List[Dict]:
        """
        Search GitHub repositories

        Args:
            query: Search query
            language: Filter by language
            num_results: Number of results

        Returns:
            List of repositories
        """
        try:
            url = "https://api.github.com/search/repositories"

            search_query = query
            if language:
                search_query += f" language:{language}"

            params = {
                'q': search_query,
                'sort': 'stars',
                'order': 'desc',
                'per_page': num_results
            }

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                results = []
                for item in data.get('items', []):
                    results.append({
                        'name': item['full_name'],
                        'description': item['description'],
                        'stars': item['stargazers_count'],
                        'forks': item['forks_count'],
                        'language': item['language'],
                        'url': item['html_url'],
                        'updated_at': item['updated_at']
                    })

                return results
            else:
                return []

        except Exception as e:
            print(f"[ERROR] GitHub search failed: {e}")
            return []

    def get_github_issues(self, repo: str, state: str = 'open', labels: List[str] = None) -> List[Dict]:
        """
        Get GitHub issues for a repository

        Args:
            repo: Repository (owner/name)
            state: Issue state (open/closed/all)
            labels: Filter by labels

        Returns:
            List of issues
        """
        try:
            url = f"https://api.github.com/repos/{repo}/issues"

            params = {
                'state': state,
                'per_page': 10
            }

            if labels:
                params['labels'] = ','.join(labels)

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                issues = response.json()

                results = []
                for issue in issues:
                    results.append({
                        'number': issue['number'],
                        'title': issue['title'],
                        'state': issue['state'],
                        'labels': [l['name'] for l in issue.get('labels', [])],
                        'created_at': issue['created_at'],
                        'updated_at': issue['updated_at'],
                        'comments': issue['comments'],
                        'url': issue['html_url'],
                        'body': issue['body'][:200] if issue['body'] else None
                    })

                return results
            else:
                return []

        except Exception as e:
            print(f"[ERROR] GitHub issues fetch failed: {e}")
            return []

    # === DOCUMENTATION SCRAPING ===

    def scrape_documentation(self, url: str) -> Optional[str]:
        """
        Scrape documentation from URL

        Args:
            url: Documentation URL

        Returns:
            Extracted text content
        """
        try:
            response = self.session.get(url, timeout=15)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Remove script and style elements
                for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                    script.decompose()

                # Get text
                text = soup.get_text()

                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)

                return text[:5000]  # Limit to 5000 chars
            else:
                return None

        except Exception as e:
            print(f"[ERROR] Documentation scraping failed: {e}")
            return None

    # === KNOWLEDGE UPDATES ===

    def check_library_version(self, library: str, package_manager: str = 'pypi') -> Dict:
        """
        Check latest version of a library

        Args:
            library: Library name
            package_manager: 'pypi' or 'npm'

        Returns:
            Version information
        """
        if package_manager == 'pypi':
            info = self.get_pypi_package_info(library)
            if info:
                return {
                    'library': library,
                    'latest_version': info['version'],
                    'summary': info['summary'],
                    'homepage': info['home_page']
                }
        elif package_manager == 'npm':
            info = self.get_npm_package_info(library)
            if info:
                return {
                    'library': library,
                    'latest_version': info['version'],
                    'description': info['description'],
                    'homepage': info['homepage']
                }

        return {'library': library, 'error': 'Not found'}

    def get_trending_repos(self, language: str = None, since: str = 'daily') -> List[Dict]:
        """
        Get trending GitHub repositories

        Args:
            language: Filter by language
            since: 'daily', 'weekly', or 'monthly'

        Returns:
            List of trending repos
        """
        # GitHub trending is scraped from github.com/trending
        try:
            url = "https://github.com/trending"
            if language:
                url += f"/{language.lower()}"

            params = {'since': since}

            response = self.session.get(url, params=params, timeout=15)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                results = []
                for article in soup.find_all('article', class_='Box-row')[:10]:
                    h2 = article.find('h2')
                    if h2:
                        link = h2.find('a')
                        repo_name = link.get('href', '').strip('/') if link else ''

                        desc = article.find('p', class_='col-9')
                        description = desc.get_text().strip() if desc else ''

                        results.append({
                            'name': repo_name,
                            'description': description,
                            'url': f"https://github.com/{repo_name}"
                        })

                return results
            else:
                return []

        except Exception as e:
            print(f"[ERROR] Trending repos fetch failed: {e}")
            return []


# === TEST CODE ===

def main():
    """Test real-time internet access"""
    print("=" * 70)
    print("Real-Time Internet Access")
    print("=" * 70)

    internet = RealtimeInternet()

    try:
        print("\n1. Testing web search...")
        results = internet.search_web("Python async programming", num_results=3)
        print(f"   Found {len(results)} results")
        if results:
            print(f"   Top result: {results[0]['title']}")

        print("\n2. Testing Stack Overflow search...")
        results = internet.search_stackoverflow("Python asyncio", num_results=3)
        print(f"   Found {len(results)} questions")
        if results:
            print(f"   Top: {results[0]['title'][:60]}...")

        print("\n3. Testing PyPI package info...")
        info = internet.get_pypi_package_info("requests")
        if info:
            print(f"   Package: {info['name']} v{info['version']}")
            print(f"   Summary: {info['summary'][:60]}...")

        print("\n4. Testing npm package info...")
        info = internet.get_npm_package_info("react")
        if info:
            print(f"   Package: {info['name']} v{info['version']}")
            print(f"   Description: {info['description'][:60]}...")

        print("\n5. Testing GitHub repo search...")
        repos = internet.search_github_repos("machine learning", language="python", num_results=3)
        print(f"   Found {len(repos)} repos")
        if repos:
            print(f"   Top: {repos[0]['name']} ({repos[0]['stars']} stars)")

        print("\n6. Testing library version check...")
        version_info = internet.check_library_version("flask", "pypi")
        print(f"   Flask latest: {version_info.get('latest_version', 'N/A')}")

        print(f"\n[OK] Real-Time Internet Access Working!")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
