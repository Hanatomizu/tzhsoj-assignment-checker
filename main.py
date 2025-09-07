import sys
import requests
from bs4 import BeautifulSoup
import time
import json
from typing import List, Dict, Optional
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TZHSOJScraper:
    def __init__(self, base_url: str = "https://tzhsoj.cn"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def fetch_submissions(self, uid_or_name: str, pid: str, max_pages: int = 10) -> List[Dict]:
        """
        获取指定用户和题目的提交记录

        Args:
            uid_or_name: 用户ID或用户名
            pid: 题目ID
            max_pages: 最大爬取页数

        Returns:
            提交记录列表
        """
        submissions = []
        page = 1

        while page <= max_pages:
            logger.info(f"Getting submission from page{page} ...")

            # 构建请求URL
            params = {
                'uidOrName': uid_or_name,
                'pid': pid,
                'tid': '',
                'lang': '',
                'status': '',
                'page': page
            }

            try:
                response = self.session.get(f"{self.base_url}/record", params=params, timeout=10)
                response.raise_for_status()

                # 解析HTML
                page_submissions = self.parse_submission_page(response.text)
                if not page_submissions:
                    logger.info("No more submissions")
                    break

                submissions.extend(page_submissions)
                logger.info(f"Page {page} fetched {len(page_submissions)} submissions")

                # 检查是否有下一页
                if not self.has_next_page(response.text):
                    logger.info("Arrived at last page")
                    break

                page += 1
                time.sleep(1)  # 礼貌性延迟，避免请求过快

            except requests.exceptions.RequestException as e:
                logger.error(f"Error occurred on {page}: {e}")
                break

        return submissions

    def parse_submission_page(self, html: str) -> List[Dict]:
        """
        解析提交记录页面HTML

        Args:
            html: 页面HTML内容

        Returns:
            解析后的提交记录列表
        """
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')

        if not table:
            return []

        submissions = []
        rows = table.find_all('tr')[1:]  # 跳过表头

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 7:  # 确保有足够的列
                continue

            try:
                submission = {
                    'time': cols[0].get_text(strip=True),
                    'problem': cols[1].get_text(strip=True),
                    'user': cols[2].get_text(strip=True),
                    'language': cols[3].get_text(strip=True),
                    'status': cols[4].get_text(strip=True),
                    'score': cols[5].get_text(strip=True),
                    'time_used': cols[6].get_text(strip=True),
                    'memory_used': cols[7].get_text(strip=True) if len(cols) > 7 else 'N/A'
                }
                submissions.append(submission)
            except Exception as e:
                logger.warning(f"Error on parsing line: {e}")
                continue

        return submissions

    def has_next_page(self, html: str) -> bool:
        """
        检查是否有下一页

        Args:
            html: 页面HTML内容

        Returns:
            是否存在下一页
        """
        soup = BeautifulSoup(html, 'html.parser')
        next_button = soup.find('a', string='Next')
        return next_button is not None and 'disabled' not in next_button.get('class', [])

    def save_to_file(self, submissions: List[Dict], filename: str):
        """
        将提交记录保存到文件

        Args:
            submissions: 提交记录列表
            filename: 文件名
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(submissions, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(submissions)} records to {filename}")

result = {}

def checker(username: str, pid: str):
    scraper = TZHSOJScraper()

    submissions = scraper.fetch_submissions(username, pid, max_pages=5)

    print(f"Fetched {len(submissions)} submissions in total")
    for i, sub in enumerate(submissions, 1):
        print(f"{i}. [{sub['time']}] {sub['problem']} - {sub['status']} ({sub['score']})")
        if sub['time'] == "100Accepted":
            result[username].append(1)
            break
    else:
        result[username].append(0)

    output_file = f"submissions_{username}_{pid}.json"
    scraper.save_to_file(submissions, output_file)


def main():
    if len(sys.argv) < 4:
        print("Arguments: main.py [usernameFormat] [Member Count] [pid].")
        return

    usernameFormat = sys.argv[1]
    counts = int(sys.argv[2])
    pids = sys.argv[3:]
    for i in range(1, counts+1):
        username = usernameFormat+str(i) if i > 9 else usernameFormat + '0' + str(i)
        result[username] = []
        for pid in pids:
            checker(username, pid)
    df = pd.DataFrame.from_dict(result, orient='index', columns=pids)
    df.to_excel("result.xlsx")

if __name__ == "__main__":
    main()
